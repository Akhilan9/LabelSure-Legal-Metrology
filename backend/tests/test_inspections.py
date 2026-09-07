import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base
from app.main import create_app
from app.models.inspection import ImportStatus, Inspection, InspectionStatus
from app.models.user import Role, User


@pytest.fixture
def phase3_client(tmp_path):
    storage_dir = tmp_path / "storage"
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite://",
        jwt_secret=secrets.token_urlsafe(48),
        storage_local_dir=str(storage_dir),
        max_upload_size_mb=5,
        max_images_per_inspection=10,
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
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_inspection_success(phase3_client):
    headers = auth_headers(phase3_client, "inspector1@labelsure.local")
    payload = {
        "product_name": "Premium Basmati Rice",
        "brand_name": "Royal Feast",
        "category": "Food & Grains",
        "package_type": "Pouch",
        "import_status": "DOMESTIC",
        "barcode": "8901030384729",
        "manufacturer_name": "Agro Foods Ltd.",
        "packer_name": "Royal Packaging Corp.",
        "importer_name": None,
        "notes": "Sample collected from supermarket shelf.",
    }
    response = phase3_client.post("/api/v1/inspections", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["inspection_code"].startswith("INS-")
    assert data["status"] == "DRAFT"
    assert data["product_name"] == "Premium Basmati Rice"
    assert data["brand_name"] == "Royal Feast"
    assert data["created_by_user_id"] == "inspector-1-id"
    assert data["created_by_name"] == "Inspector One"
    assert data["images_count"] == 0
    assert data["images"] == []
    assert data["submitted_at"] is None


def test_create_inspection_optional_fields(phase3_client):
    headers = auth_headers(phase3_client, "inspector1@labelsure.local")
    # All product context fields are optional
    response = phase3_client.post("/api/v1/inspections", json={}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"
    assert data["product_name"] is None
    assert data["import_status"] == "UNKNOWN"


def test_sequential_inspection_codes(phase3_client):
    headers = auth_headers(phase3_client, "inspector1@labelsure.local")
    res1 = phase3_client.post("/api/v1/inspections", json={"product_name": "Item 1"}, headers=headers)
    res2 = phase3_client.post("/api/v1/inspections", json={"product_name": "Item 2"}, headers=headers)
    assert res1.status_code == 201
    assert res2.status_code == 201
    code1 = res1.json()["inspection_code"]
    code2 = res2.json()["inspection_code"]
    assert code1 != code2
    assert int(code2.split("-")[-1]) == int(code1.split("-")[-1]) + 1


def test_unauthenticated_requests_rejected(phase3_client):
    assert phase3_client.post("/api/v1/inspections", json={}).status_code == 401
    assert phase3_client.get("/api/v1/inspections").status_code == 401


def test_single_role_inspector_access(phase3_client):
    headers_sup = auth_headers(phase3_client, "supervisor@labelsure.local")
    headers_insp = auth_headers(phase3_client, "inspector1@labelsure.local")

    # Inspector / Supervisor create inspection
    res_sup = phase3_client.post("/api/v1/inspections", json={"product_name": "Sup Item"}, headers=headers_sup)
    assert res_sup.status_code == 201

    # Inspector 1 creates inspection
    create_res = phase3_client.post("/api/v1/inspections", json={"product_name": "Test"}, headers=headers_insp)
    insp_id = create_res.json()["id"]

    # Inspector read
    assert phase3_client.get(f"/api/v1/inspections/{insp_id}", headers=headers_insp).status_code == 200


def test_cross_inspector_isolation(phase3_client):
    headers1 = auth_headers(phase3_client, "inspector1@labelsure.local")
    headers2 = auth_headers(phase3_client, "inspector2@labelsure.local")

    create_res = phase3_client.post("/api/v1/inspections", json={"product_name": "Secret 1"}, headers=headers1)
    insp_id = create_res.json()["id"]

    # Inspector 2 cannot view Inspector 1's inspection (returns 404 to avoid leaking existence)
    assert phase3_client.get(f"/api/v1/inspections/{insp_id}", headers=headers2).status_code == 404

    # Inspector 2 cannot edit Inspector 1's inspection
    assert phase3_client.patch(f"/api/v1/inspections/{insp_id}", json={"product_name": "Modified"}, headers=headers2).status_code == 404


def test_list_and_search_inspections(phase3_client):
    headers1 = auth_headers(phase3_client, "inspector1@labelsure.local")
    headers2 = auth_headers(phase3_client, "inspector2@labelsure.local")

    phase3_client.post("/api/v1/inspections", json={"product_name": "Alpha Juice", "brand_name": "AlphaCorp"}, headers=headers1)
    phase3_client.post("/api/v1/inspections", json={"product_name": "Beta Milk", "brand_name": "BetaDairy"}, headers=headers1)
    phase3_client.post("/api/v1/inspections", json={"product_name": "Gamma Oil", "brand_name": "GammaFoods"}, headers=headers2)

    # Inspector 1 list sees only their 2
    res_insp1 = phase3_client.get("/api/v1/inspections", headers=headers1)
    assert res_insp1.status_code == 200
    assert res_insp1.json()["total"] == 2

    # Inspector 1 search
    res_search = phase3_client.get("/api/v1/inspections?q=Alpha", headers=headers1)
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["product_name"] == "Alpha Juice"

