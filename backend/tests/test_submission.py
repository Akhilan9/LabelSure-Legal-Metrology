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

SAMPLE_JPEG = create_valid_jpeg()


@pytest.fixture
def sub_client(tmp_path):
    storage_dir = tmp_path / "storage"
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite://",
        jwt_secret=secrets.token_urlsafe(48),
        storage_local_dir=str(storage_dir),
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


def test_submit_without_evidence_fails(sub_client):
    headers = auth_headers(sub_client, "inspector1@labelsure.local")
    insp = sub_client.post("/api/v1/inspections", json={"product_name": "No Image Item"}, headers=headers).json()
    insp_id = insp["id"]

    res = sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert res.status_code == 422
    assert "at least one uploaded evidence image" in res.text


def test_successful_submission_flow(sub_client):
    headers = auth_headers(sub_client, "inspector1@labelsure.local")
    insp = sub_client.post("/api/v1/inspections", json={"product_name": "Ready Item", "brand_name": "Top Brand"}, headers=headers).json()
    insp_id = insp["id"]

    # Upload 1 image
    upload_res = sub_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("front.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers,
    )
    assert upload_res.status_code == 201

    # Submit
    submit_res = sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["status"] == "READY_FOR_ANALYSIS"
    assert sub_data["submitted_at"] is not None
    assert sub_data["submitted_at"].endswith("Z") or "+00:00" in sub_data["submitted_at"]


def test_double_submission_and_modification_lock(sub_client):
    headers = auth_headers(sub_client, "inspector1@labelsure.local")
    insp = sub_client.post("/api/v1/inspections", json={"product_name": "Lock Item"}, headers=headers).json()
    insp_id = insp["id"]

    # Upload image
    sub_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("front.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers,
    )

    # Submit once
    assert sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers).status_code == 200

    # Submit again -> 409 Conflict
    res_again = sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert res_again.status_code == 409

    # Edit product info -> 409 Conflict
    res_patch = sub_client.patch(f"/api/v1/inspections/{insp_id}", json={"product_name": "New Name"}, headers=headers)
    assert res_patch.status_code == 409

    # Upload more images -> 409 Conflict
    res_up = sub_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("another.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers,
    )
    assert res_up.status_code == 409


def test_submission_rbac_enforcement(sub_client):
    headers_insp1 = auth_headers(sub_client, "inspector1@labelsure.local")
    headers_insp2 = auth_headers(sub_client, "inspector2@labelsure.local")
    headers_sup = auth_headers(sub_client, "supervisor@labelsure.local")

    insp = sub_client.post("/api/v1/inspections", json={"product_name": "RBAC Item"}, headers=headers_insp1).json()
    insp_id = insp["id"]
    sub_client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files=[("files", ("front.jpg", SAMPLE_JPEG, "image/jpeg"))],
        headers=headers_insp1,
    )

    # Inspector 2 submit -> 404 (not found / not owned)
    assert sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers_insp2).status_code == 404

    # Supervisor submit -> 403 Forbidden
    assert sub_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers_sup).status_code == 403
