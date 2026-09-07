from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    settings = Settings(_env_file=None, environment="test", database_url="sqlite://")
    with TestClient(create_app(settings)) as instance:
        yield instance


def test_health_checks_real_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    with client.app.state.session_factory() as session:
        assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_unavailable_database_is_503_without_details(client):
    with patch.object(client.app.state.engine, "connect", side_effect=OperationalError(
        "sensitive connection string", {}, Exception("private")
    )):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "private" not in response.text


def test_cors_allows_configured_origin(client):
    response = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"
    })
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    response = client.options("/api/v1/health", headers={
        "Origin": "https://unknown.example", "Access-Control-Request-Method": "GET"
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_cors_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["*"])


def test_future_features_not_exposed(client):
    assert client.post("/api/v1/rules").status_code == 404
