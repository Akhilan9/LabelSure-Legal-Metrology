import io
import secrets
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base
from app.main import create_app
from app.models.user import Role, User

import cv2
import numpy as np

def create_valid_jpeg() -> bytes:
    img = np.full((800, 800, 3), 180, dtype=np.uint8)
    cv2.putText(img, "TEST IMAGE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()

def create_valid_png() -> bytes:
    img = np.full((800, 800, 3), 180, dtype=np.uint8)
    cv2.putText(img, "TEST PNG", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

SAMPLE_JPEG = create_valid_jpeg()
SAMPLE_PNG = create_valid_png()
SAMPLE_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01*\x01\x00\x01\x00\x00"


@pytest.fixture
def image_client(tmp_path):
    storage_dir = tmp_path / "storage"
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite://",
        jwt_secret=secrets.token_urlsafe(48),
        storage_local_dir=str(storage_dir),
        max_upload_size_mb=1,  # 1 MB for testing limits
        max_images_per_inspection=3,  # 3 images max for testing
    )
    with TestClient(create_app(settings)) as client:
        Base.metadata.create_all(client.app.state.engine)
        password = "TestPassword123!"
        hashed = hash_password(password)
        with client.app.state.session_factory() as session:
            session.add_all([
                User(id="admin-id", full_name="Admin User", email="admin@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="inspector-1-id", full_name="Inspector One", email="inspector1@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="inspector-2-id", full_name="Inspector Two", email="inspector2@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="supervisor-id", full_name="Supervisor User", email="supervisor@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
            ])
            session.commit()
        client.test_password = password
        yield client


def auth_headers(client, email="inspector1@labelsure.local"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": client.test_password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_single_image_success(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Test Snack"}, headers=headers).json()
    insp_id = insp["id"]

    files = [("files", ("front_panel.jpg", SAMPLE_JPEG, "image/jpeg"))]
    data = {"panel_types": ["FRONT"]}

    upload_res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_res.status_code == 201
    img_data = upload_res.json()
    assert len(img_data) == 1
    assert img_data[0]["original_filename"] == "front_panel.jpg"
    assert img_data[0]["panel_type"] == "FRONT"
    assert img_data[0]["mime_type"] == "image/jpeg"
    assert len(img_data[0]["sha256"]) == 64
    assert img_data[0]["content_url"] != ""

    # Check inspection status transitioned to EVIDENCE_UPLOADED
    get_insp = image_client.get(f"/api/v1/inspections/{insp_id}", headers=headers).json()
    assert get_insp["status"] == "EVIDENCE_UPLOADED"
    assert get_insp["images_count"] == 1


def test_upload_multiple_images_with_panels(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Multi Image"}, headers=headers).json()
    insp_id = insp["id"]

    files = [
        ("files", ("front.jpg", SAMPLE_JPEG, "image/jpeg")),
        ("files", ("back.png", SAMPLE_PNG, "image/png")),
    ]
    data = {"panel_types": ["FRONT", "DECLARATION_PANEL"]}

    res = image_client.post(f"/api/v1/inspections/{insp_id}/images", files=files, data=data, headers=headers)
    assert res.status_code == 201
    images = res.json()
    assert len(images) == 2
    assert images[0]["panel_type"] == "FRONT"
    assert images[1]["panel_type"] == "DECLARATION_PANEL"


def test_upload_rejections(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Reject Tests"}, headers=headers).json()
    insp_id = insp["id"]

    # 1. Zero-byte file
    res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("empty.jpg", b"", "image/jpeg"))],
        headers=headers,
    )
    assert res.status_code == 422
    assert "empty" in res.text

    # 2. Oversized file (> 1 MB)
    large_data = SAMPLE_JPEG + (b"\x00" * (1024 * 1024 + 50))
    res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("large.jpg", large_data, "image/jpeg"))],
        headers=headers,
    )
    assert res.status_code == 422
    assert "maximum allowed size" in res.text

    # 3. Disguised fake image (text pretending to be .jpg)
    res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("fake.jpg", b"hello world this is text", "image/jpeg"))],
        headers=headers,
    )
    assert res.status_code == 422
    assert "Allowed formats" in res.text


def test_max_images_limit_enforced(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Max Limit"}, headers=headers).json()
    insp_id = insp["id"]

    files = [
        ("files", ("img1.jpg", SAMPLE_JPEG, "image/jpeg")),
        ("files", ("img2.png", SAMPLE_PNG, "image/png")),
        ("files", ("img3.webp", SAMPLE_WEBP, "image/webp")),
        ("files", ("img4.jpg", SAMPLE_JPEG, "image/jpeg")),  # 4th image exceeds max limit of 3
    ]
    res = image_client.post(f"/api/v1/inspections/{insp_id}/images", files=files, headers=headers)
    assert res.status_code == 422
    assert "exceed maximum of 3" in res.text


def test_get_image_content(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Content Test"}, headers=headers).json()
    insp_id = insp["id"]

    upload_res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("test.png", SAMPLE_PNG, "image/png"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    content_res = image_client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/content", headers=headers)
    assert content_res.status_code == 200
    assert content_res.headers["content-type"] == "image/png"
    assert content_res.content == SAMPLE_PNG


def test_update_image_panel_and_delete(image_client):
    headers = auth_headers(image_client, "inspector1@labelsure.local")
    insp = image_client.post("/api/v1/inspections", json={"product_name": "Panel Test"}, headers=headers).json()
    insp_id = insp["id"]

    upload_res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("test.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers,
    )
    img_id = upload_res.json()[0]["id"]

    # Patch panel
    patch_res = image_client.patch(
        f"/api/v1/inspections/{insp_id}/images/{img_id}",
        json={"panel_type": "MRP_PANEL"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["panel_type"] == "MRP_PANEL"

    # Delete image
    del_res = image_client.delete(f"/api/v1/inspections/{insp_id}/images/{img_id}", headers=headers)
    assert del_res.status_code == 200

    # Inspection status reverts to DRAFT
    get_insp = image_client.get(f"/api/v1/inspections/{insp_id}", headers=headers).json()
    assert get_insp["status"] == "DRAFT"
    assert get_insp["images_count"] == 0


def test_supervisor_read_only_evidence_access(image_client):
    headers_insp = auth_headers(image_client, "inspector1@labelsure.local")
    headers_sup = auth_headers(image_client, "supervisor@labelsure.local")

    insp = image_client.post("/api/v1/inspections", json={"product_name": "Sup Evidence"}, headers=headers_insp).json()
    insp_id = insp["id"]

    upload_res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("img.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers_insp,
    )
    img_id = upload_res.json()[0]["id"]

    # In single-role model, non-owner inspector receives 404
    assert image_client.get(f"/api/v1/inspections/{insp_id}/images", headers=headers_sup).status_code == 404


def test_cross_inspector_cannot_access_images(image_client):
    headers1 = auth_headers(image_client, "inspector1@labelsure.local")
    headers2 = auth_headers(image_client, "inspector2@labelsure.local")

    insp = image_client.post("/api/v1/inspections", json={"product_name": "Private Snack"}, headers=headers1).json()
    insp_id = insp["id"]

    upload_res = image_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("private.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers1,
    )
    img_id = upload_res.json()[0]["id"]

    # Inspector 2 gets 404
    assert image_client.get(f"/api/v1/inspections/{insp_id}/images", headers=headers2).status_code == 404
    assert image_client.get(f"/api/v1/inspections/{insp_id}/images/{img_id}/content", headers=headers2).status_code == 404
    assert image_client.post(f"/api/v1/inspections/{insp_id}/images", files=[("files", ("hack.jpg", SAMPLE_JPEG, "image/jpeg"))], headers=headers2).status_code == 404
    assert image_client.patch(f"/api/v1/inspections/{insp_id}/images/{img_id}", json={"panel_type": "BACK"}, headers=headers2).status_code == 404
    assert image_client.delete(f"/api/v1/inspections/{insp_id}/images/{img_id}", headers=headers2).status_code == 404

