import secrets
from uuid import uuid4

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base
from app.main import create_app
from app.models.ocr import OCRConfidenceTier, OCRStatus
from app.models.user import Role, User
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.service import set_custom_ocr_provider


def create_test_image_bytes(width: int = 800, height: int = 800) -> bytes:
    img = np.full((height, width, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (780, 100), (30, 30, 30), -1)
    cv2.putText(img, "APEX ORGANIC OATS", (40, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    cv2.putText(img, "Net Quantity: 1 kg", (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    cv2.putText(img, "MRP: Rs. 350.00 (Incl. Taxes)", (40, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    cv2.putText(img, "Pkg Date: 08/2026", (40, 340), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    success, buffer = cv2.imencode(".jpg", img)
    assert success
    return buffer.tobytes()


@pytest.fixture
def client(tmp_path):
    storage_dir = tmp_path / "storage"
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite://",
        jwt_secret=secrets.token_urlsafe(48),
        storage_local_dir=str(storage_dir),
        max_upload_size_mb=5,
        max_images_per_inspection=5,
        ocr_provider="mock",
        ocr_confidence_good=0.85,
        ocr_confidence_review=0.60,
        ruleset_id="labelsure_prototype",
    )
    with TestClient(create_app(settings)) as client:
        Base.metadata.create_all(client.app.state.engine)
        password = "TestPassword123!"
        hashed = hash_password(password)
        with client.app.state.session_factory() as session:
            session.add_all([
                User(id="admin-id", full_name="Admin User", email="admin@labelsure.local", hashed_password=hashed, role=Role.ADMIN),
                User(id="inspector-1-id", full_name="Inspector One", email="inspector1@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="inspector-2-id", full_name="Inspector Two", email="inspector2@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="supervisor-id", full_name="Supervisor User", email="supervisor@labelsure.local", hashed_password=hashed, role=Role.SUPERVISOR),
            ])
            session.commit()
        client.test_password = password
        # Ensure default mock provider is clean
        set_custom_ocr_provider(None)
        yield client
        set_custom_ocr_provider(None)


def auth_headers(client, email="inspector1@labelsure.local"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": client.test_password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ocr_single_image_end_to_end(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Organic Honey 500g"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("front_panel.jpg", img_bytes, "image/jpeg"))],
        data={"panel_types": ["FRONT"]},
        headers=headers,
    )
    assert upload_res.status_code == 201
    img_id = upload_res.json()[0]["id"]

    # 1. Run Phase 4 Preprocessing first
    proc_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers)
    assert proc_res.status_code == 200

    # 2. Trigger OCR on image
    ocr_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=headers)
    assert ocr_res.status_code == 200
    data = ocr_res.json()

    assert data["inspection_id"] == insp_id
    assert data["inspection_image_id"] == img_id
    assert data["engine_name"] == "MockOCR"
    assert data["status"] == "SUCCESS"
    assert data["block_count"] >= 4
    assert data["average_confidence"] is not None
    assert len(data["blocks"]) >= 4

    # Verify block structure
    first_block = data["blocks"][0]
    assert "raw_text" in first_block
    assert "normalized_text" in first_block
    assert "confidence" in first_block
    assert "confidence_tier" in first_block
    assert "polygon" in first_block
    assert len(first_block["polygon"]) == 4
    assert "bounding_box" in first_block
    assert first_block["reading_order"] == 0


def test_ocr_idempotency_and_force(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Almond Milk"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("carton.jpg", img_bytes, "image/jpeg"))],
        data={"panel_types": ["FRONT"]},
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Run OCR first time
    run1 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=headers).json()
    run1_id = run1["id"]

    # Run OCR second time without force -> returns cached run
    run2 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=headers).json()
    assert run2["id"] == run1_id

    # Run OCR with force=true -> creates new run
    run3 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr?force=true", headers=headers).json()
    assert run3["id"] != run1_id
    assert run3["status"] == "SUCCESS"


def test_batch_ocr_and_summary(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Multi-Panel Biscuit Pack"}, headers=headers).json()
    insp_id = insp["id"]

    # Upload 2 images: Front and Nutrition
    img1_bytes = create_test_image_bytes(800, 800)
    img2_bytes = create_test_image_bytes(800, 800)

    client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[
            ("files", ("front.jpg", img1_bytes, "image/jpeg")),
            ("files", ("nutrition.jpg", img2_bytes, "image/jpeg")),
        ],
        data={"panel_types": ["FRONT", "NUTRITION_FACTS"]},
        headers=headers,
    )

    # Trigger batch OCR across all panels
    batch_res = client.post(f"/api/v1/inspections/{insp_id}/ocr", headers=headers)
    assert batch_res.status_code == 200
    batch_data = batch_res.json()

    assert batch_data["total_images"] == 2
    assert batch_data["success"] == 2
    assert batch_data["failed"] == 0
    assert len(batch_data["results"]) == 2

    # Fetch OCR summary
    summary_res = client.get(f"/api/v1/inspections/{insp_id}/ocr/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary["inspection_id"] == insp_id
    assert summary["total_images"] == 2
    assert summary["ocr_completed_count"] == 2
    assert summary["ocr_failed_count"] == 0
    assert summary["total_ocr_blocks"] >= 8
    assert summary["average_confidence"] is not None
    assert len(summary["panels"]) == 2


def test_get_ocr_blocks_endpoint(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Block Test Item"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("panel.jpg", img_bytes, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Process OCR
    client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=headers)

    # Query blocks endpoint
    blocks_res = client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr/blocks", headers=headers)
    assert blocks_res.status_code == 200
    blocks = blocks_res.json()
    assert isinstance(blocks, list)
    assert len(blocks) >= 4
    assert blocks[0]["reading_order"] == 0


def test_ocr_rbac_and_idor(client):
    insp1_headers = auth_headers(client, "inspector1@labelsure.local")
    insp2_headers = auth_headers(client, "inspector2@labelsure.local")
    admin_headers = auth_headers(client, "admin@labelsure.local")
    sup_headers = auth_headers(client, "supervisor@labelsure.local")

    # Inspector 1 creates inspection
    insp = client.post("/api/v1/inspections", json={"product_name": "RBAC Item"}, headers=insp1_headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("img.jpg", img_bytes, "image/jpeg"))],
        headers=insp1_headers,
    )
    img_id = upload_res.json()[0]["id"]

    # 1. Unauthenticated request -> 401
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr").status_code == 401
    assert client.get(f"/api/v1/inspections/{insp_id}/ocr/summary").status_code == 401

    # 2. Inspector 2 (cross-inspector non-owner) -> 404 (IDOR protection)
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=insp2_headers).status_code == 404
    assert client.get(f"/api/v1/inspections/{insp_id}/ocr/summary", headers=insp2_headers).status_code == 404

    # 3. Supervisor triggers mutation -> 403 Forbidden
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=sup_headers).status_code == 403
    assert client.post(f"/api/v1/inspections/{insp_id}/ocr", headers=sup_headers).status_code == 403

    # 4. Inspector 1 triggers OCR -> 200 OK
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=insp1_headers).status_code == 200

    # 5. Supervisor reads OCR run & summary -> 200 OK
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=sup_headers).status_code == 200
    assert client.get(f"/api/v1/inspections/{insp_id}/ocr/summary", headers=sup_headers).status_code == 200

    # 6. Admin has full access (mutations + reads) -> 200 OK
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr?force=true", headers=admin_headers).status_code == 200
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=admin_headers).status_code == 200


def test_ocr_provider_failure_handling(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Failure Test Item"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("fail.jpg", img_bytes, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Inject failing mock provider
    custom_mock = MockOCRProvider(simulate_failure=True, failure_error_code="MODEL_TIMEOUT", failure_error_message="OCR Timeout")
    set_custom_ocr_provider(custom_mock)

    try:
        ocr_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", headers=headers)
        assert ocr_res.status_code == 200
        data = ocr_res.json()

        assert data["status"] == "FAILED"
        assert data["error_code"] == "MODEL_TIMEOUT"
        assert data["error_message_safe"] == "OCR Timeout"
        assert len(data["blocks"]) == 0
    finally:
        set_custom_ocr_provider(None)
