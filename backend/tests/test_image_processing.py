import io
import secrets
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base
from app.main import create_app
from app.models.image_quality import QualityStatus
from app.models.user import Role, User


def create_test_image_bytes(width: int = 800, height: int = 800) -> bytes:
    img = np.full((height, width, 3), 180, dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (760, 120), (30, 30, 30), -1)
    cv2.putText(img, "PACKAGED COMMODITY", (60, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(img, "NET QUANTITY: 1 kg", (60, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
    cv2.putText(img, "MRP: Rs. 299.00", (60, 320), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
    cv2.rectangle(img, (40, 140), (740, 500), (10, 10, 10), 3)
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
        yield client


def auth_headers(client, email="inspector1@labelsure.local"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": client.test_password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_process_single_image_end_to_end(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Premium Tea 500g"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("label.jpg", img_bytes, "image/jpeg"))],
        data={"panel_types": ["FRONT"]},
        headers=headers,
    )
    assert upload_res.status_code == 201
    img_id = upload_res.json()[0]["id"]
    original_sha = upload_res.json()[0]["sha256"]

    # 1. Trigger image processing
    proc_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers)
    assert proc_res.status_code == 200
    data = proc_res.json()

    assert data["inspection_image_id"] == img_id
    assert data["quality_status"] == "GOOD"
    assert data["width"] == 800
    assert data["height"] == 800
    assert data["metrics"]["blur_score"] is not None
    assert data["metrics"]["brightness_score"] is not None
    assert data["metrics"]["contrast_score"] is not None
    assert data["metrics"]["glare_score"] is not None
    assert data["derived_image_available"] is True
    assert data["derived_content_url"] == f"/api/v1/inspections/{insp_id}/images/{img_id}/processed"
    assert len(data["derived_sha256"]) == 64

    # 2. Fetch derived preprocessed image stream
    derived_res = client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/processed", headers=headers)
    assert derived_res.status_code == 200
    assert derived_res.headers["content-type"] == "image/png"
    assert derived_res.content[:8] == b"\x89PNG\r\n\x1a\n"

    # 3. Verify original evidence remains strictly immutable
    orig_res = client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/content", headers=headers)
    assert orig_res.status_code == 200
    assert orig_res.content == img_bytes

    # 4. Fetch inspection and check image response has processing_result attached
    get_insp = client.get(f"/api/v1/inspections/{insp_id}", headers=headers).json()
    assert get_insp["images"][0]["processing_result"] is not None
    assert get_insp["images"][0]["processing_result"]["quality_status"] == "GOOD"


def test_process_single_image_idempotency(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Idempotent Check"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("label.jpg", img_bytes, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # First run
    res1 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers).json()
    proc_id_1 = res1["id"]
    processed_at_1 = res1["processed_at"]

    # Second run without force
    res2 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers).json()
    assert res2["id"] == proc_id_1
    assert res2["processed_at"] == processed_at_1

    # Third run with force=True
    res3 = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process?force=true", headers=headers).json()
    assert res3["id"] == proc_id_1
    assert res3["quality_status"] == "GOOD"


def test_batch_process_images(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Batch Process Test"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes_1 = create_test_image_bytes(800, 800)
    img_bytes_2 = create_test_image_bytes(900, 900)

    client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[
            ("files", ("img1.jpg", img_bytes_1, "image/jpeg")),
            ("files", ("img2.jpg", img_bytes_2, "image/jpeg")),
        ],
        headers=headers,
    )

    batch_res = client.post(f"/api/v1/inspections/{insp_id}/process-images", headers=headers)
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["total_processed"] == 2
    assert batch_data["successful_count"] == 2
    assert batch_data["failed_count"] == 0
    assert len(batch_data["results"]) == 2


def test_get_image_quality_endpoint(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Quality Query"}, headers=headers).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("label.jpg", img_bytes, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Before processing -> 404
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/quality", headers=headers).status_code == 404

    # Process
    client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers)

    # After processing -> 200
    qual_res = client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/quality", headers=headers)
    assert qual_res.status_code == 200
    assert qual_res.json()["quality_status"] == "GOOD"


def test_rbac_and_idor_on_image_processing(client):
    headers1 = auth_headers(client, "inspector1@labelsure.local")
    headers2 = auth_headers(client, "inspector2@labelsure.local")
    headers_sup = auth_headers(client, "supervisor@labelsure.local")
    headers_admin = auth_headers(client, "admin@labelsure.local")

    insp = client.post("/api/v1/inspections", json={"product_name": "RBAC Processing"}, headers=headers1).json()
    insp_id = insp["id"]

    img_bytes = create_test_image_bytes(800, 800)
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("label.jpg", img_bytes, "image/jpeg"))],
        headers=headers1,
    )
    img_id = upload_res.json()[0]["id"]

    # 1. Inspector 2 (non-owner) gets 404 on process, quality, and processed streams
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers2).status_code == 404
    assert client.post(f"/api/v1/inspections/{insp_id}/process-images", headers=headers2).status_code == 404
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/quality", headers=headers2).status_code == 404
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/processed", headers=headers2).status_code == 404

    # 2. Supervisor cannot trigger processing (403 Forbidden)
    assert client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers_sup).status_code == 403
    assert client.post(f"/api/v1/inspections/{insp_id}/process-images", headers=headers_sup).status_code == 403

    # 3. Admin can process
    admin_proc = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers_admin)
    assert admin_proc.status_code == 200

    # 4. Supervisor can now read quality metadata and processed stream
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/quality", headers=headers_sup).status_code == 200
    assert client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/processed", headers=headers_sup).status_code == 200


def test_corrupted_image_processing_failure(client):
    headers = auth_headers(client, "inspector1@labelsure.local")
    insp = client.post("/api/v1/inspections", json={"product_name": "Corrupt Image Test"}, headers=headers).json()
    insp_id = insp["id"]

    # Valid JPEG header but truncated garbage body
    corrupt_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00garbage_data"
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("corrupted.jpg", corrupt_bytes, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Processing should handle exception gracefully and return PROCESSING_FAILED
    proc_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/process", headers=headers)
    assert proc_res.status_code == 200
    data = proc_res.json()
    assert data["quality_status"] == "PROCESSING_FAILED"
    assert "PROCESSING_ERROR" in data["flags"]
    assert data["error_message"] is not None

