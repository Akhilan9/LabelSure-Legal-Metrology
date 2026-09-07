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
def dash_client(tmp_path):
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
                User(id="supervisor-id", full_name="Supervisor User", email="supervisor@labelsure.local", hashed_password=hashed, role=Role.SUPERVISOR),
                User(id="inspector-1-id", full_name="Inspector One", email="inspector1@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
                User(id="inspector-2-id", full_name="Inspector Two", email="inspector2@labelsure.local", hashed_password=hashed, role=Role.INSPECTOR),
            ])
            session.commit()
        client.test_password = password
        yield client


def auth_headers(client, email="inspector1@labelsure.local"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": client.test_password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_summary_metrics(dash_client):
    headers1 = auth_headers(dash_client, "inspector1@labelsure.local")
    headers2 = auth_headers(dash_client, "inspector2@labelsure.local")
    headers_admin = auth_headers(dash_client, "admin@labelsure.local")

    # Inspector 1 creates 1 DRAFT, 1 EVIDENCE_UPLOADED, 1 READY_FOR_ANALYSIS
    insp1 = dash_client.post("/api/v1/inspections", json={"product_name": "Draft Insp"}, headers=headers1).json()

    insp2 = dash_client.post("/api/v1/inspections", json={"product_name": "Uploaded Insp"}, headers=headers1).json()
    dash_client.post(f"/api/v1/inspections/{insp2['id']}/images", files=[("files", ("img.jpg", SAMPLE_JPEG, "image/jpeg"))], headers=headers1)

    insp3 = dash_client.post("/api/v1/inspections", json={"product_name": "Submitted Insp"}, headers=headers1).json()
    dash_client.post(f"/api/v1/inspections/{insp3['id']}/images", files=[("files", ("img.jpg", SAMPLE_JPEG, "image/jpeg"))], headers=headers1)
    dash_client.post(f"/api/v1/inspections/{insp3['id']}/submit", headers=headers1)

    # Inspector 2 creates 1 DRAFT
    dash_client.post("/api/v1/inspections", json={"product_name": "Insp 2 Draft"}, headers=headers2)

    # Check Inspector 1 dashboard summary (should only see their 3)
    dash1 = dash_client.get("/api/v1/dashboard/summary", headers=headers1).json()
    assert dash1["total_inspections"] == 3
    assert dash1["draft_count"] == 1
    assert dash1["evidence_uploaded_count"] == 1
    assert dash1["ready_for_analysis_count"] == 1
    assert len(dash1["recent_inspections"]) == 3

    # Check Admin dashboard summary (should see all 4)
    dash_admin = dash_client.get("/api/v1/dashboard/summary", headers=headers_admin).json()
    assert dash_admin["total_inspections"] == 4
    assert dash_admin["draft_count"] == 2
    assert dash_admin["evidence_uploaded_count"] == 1
    assert dash_admin["ready_for_analysis_count"] == 1
    assert len(dash_admin["recent_inspections"]) == 4


def test_enforcement_metrics_and_review_queue(dash_client):
    headers1 = auth_headers(dash_client, "inspector1@labelsure.local")
    headers_sup = auth_headers(dash_client, "supervisor@labelsure.local")

    # Create inspection with category and metadata
    insp_res = dash_client.post("/api/v1/inspections", json={
        "product_name": "Packaged Almond Milk",
        "brand_name": "NutriLife",
        "category": "FOOD",
        "package_type": "TETRA_PAK"
    }, headers=headers1).json()
    insp_id = insp_res["id"]

    # Upload evidence and submit
    dash_client.post(f"/api/v1/inspections/{insp_id}/images", files=[("files", ("label.jpg", SAMPLE_JPEG, "image/jpeg"))], headers=headers1)
    dash_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers1)

    # 1. Test /dashboard/metrics
    metrics = dash_client.get("/api/v1/dashboard/metrics", headers=headers1).json()
    assert metrics["total_inspections"] >= 1
    assert metrics["ready_for_analysis_count"] >= 1
    assert isinstance(metrics["top_violations"], list)
    assert isinstance(metrics["category_breakdown"], list)

    # 2. Test /dashboard/review-queue
    queue_res = dash_client.get("/api/v1/dashboard/review-queue", headers=headers1)
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert queue["total"] >= 1
    assert len(queue["items"]) >= 1
    item = queue["items"][0]
    assert item["inspection_id"] == insp_id
    assert item["product_name"] == "Packaged Almond Milk"
    assert item["urgency_tier"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert item["urgency_score"] >= 0.0

    # Test queue filters
    filtered_queue = dash_client.get("/api/v1/dashboard/review-queue?category=FOOD", headers=headers_sup).json()
    assert filtered_queue["total"] >= 1

    # 3. Test /dashboard/analytics
    analytics = dash_client.get("/api/v1/dashboard/analytics", headers=headers_sup).json()
    assert "average_ocr_confidence" in analytics
    assert isinstance(analytics["package_type_distribution"], list)
    assert isinstance(analytics["category_compliance"], list)
