from datetime import datetime, timedelta, timezone
import secrets

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings
from app.core.security import hash_password, issue_token
from app.db.session import Base
from app.main import create_app
from app.models.user import Role, User


@pytest.fixture
def auth_client():
    settings = Settings(_env_file=None, environment="test", database_url="sqlite://",
                        jwt_secret=secrets.token_urlsafe(48))
    with TestClient(create_app(settings)) as client:
        Base.metadata.create_all(client.app.state.engine)
        password = secrets.token_urlsafe(20)
        hashed = hash_password(password)
        with client.app.state.session_factory() as session:
            for role in Role:
                session.add(User(full_name=role.value, email=f"{role.value.lower()}@labelsure.local",
                                 hashed_password=hashed, role=role))
            session.commit()
        client.test_password = password
        yield client


def login(client, role="admin"):
    return client.post("/api/v1/auth/login", json={"email": f"{role}@labelsure.local", "password": client.test_password})


def headers(client, role="admin"):
    return {"Authorization": "Bearer " + login(client, role).json()["access_token"]}


def test_successful_login_and_me(auth_client):
    response = login(auth_client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800
    assert body["user"]["role"] == "ADMIN"
    assert "hashed_password" not in body["user"]
    assert "password" not in body["user"]
    assert response.headers["cache-control"] == "no-store"
    me = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + body["access_token"]})
    assert me.status_code == 200
    assert me.json() == body["user"]
    assert me.json()["created_at"].endswith("Z")


@pytest.mark.parametrize("email,password", [("admin@labelsure.local", "incorrect"), ("unknown@labelsure.local", "incorrect")])
def test_incorrect_credentials(auth_client, email, password):
    response = auth_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired credentials"


def test_email_normalization(auth_client):
    response = auth_client.post("/api/v1/auth/login", json={"email": " ADMIN@LABELSURE.LOCAL ", "password": auth_client.test_password})
    assert response.status_code == 200


@pytest.mark.parametrize("authorization", [None, "", "Bearer", "Basic abc", "Bearer not-a-jwt", "Bearer a b"])
def test_missing_malformed_invalid_auth(auth_client, authorization):
    response = auth_client.get("/api/v1/auth/me", headers={} if authorization is None else {"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_inactive_user_login_and_existing_token(auth_client):
    token_headers = headers(auth_client)
    with auth_client.app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.role == Role.ADMIN))
        user.is_active = False
        session.commit()
    assert login(auth_client).status_code == 401
    assert auth_client.get("/api/v1/auth/me", headers=token_headers).status_code == 401


@pytest.mark.parametrize("role,endpoint,expected", [
    ("admin", "admin", 200), ("admin", "inspection", 200), ("admin", "monitoring", 200),
    ("inspector", "admin", 403), ("inspector", "inspection", 200), ("inspector", "monitoring", 403),
    ("supervisor", "admin", 403), ("supervisor", "inspection", 403), ("supervisor", "monitoring", 200),
])
def test_role_authorization(auth_client, role, endpoint, expected):
    assert auth_client.get(f"/api/v1/dev/access/{endpoint}", headers=headers(auth_client, role)).status_code == expected


@pytest.mark.parametrize("mutation", ["expired", "wrong_signature", "missing_exp", "wrong_audience", "wrong_type", "none_algorithm", "unknown_user"])
def test_token_security(auth_client, mutation):
    settings = auth_client.app.state.settings
    token = login(auth_client).json()["access_token"]
    payload = jwt.decode(token, options={"verify_signature": False})
    key = settings.jwt_secret.get_secret_value()
    algorithm = "HS256"
    if mutation == "expired": payload["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif mutation == "wrong_signature": key = secrets.token_urlsafe(48)
    elif mutation == "missing_exp": del payload["exp"]
    elif mutation == "wrong_audience": payload["aud"] = "another-service"
    elif mutation == "wrong_type": payload["type"] = "refresh"
    elif mutation == "none_algorithm": algorithm, key = "none", ""
    elif mutation == "unknown_user": payload["sub"] = "missing-user"
    altered = jwt.encode(payload, key, algorithm=algorithm)
    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + altered})
    assert response.status_code == 401


def test_role_changes_take_effect_without_reissuing_token(auth_client):
    token_headers = headers(auth_client)
    with auth_client.app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.role == Role.ADMIN))
        user.role = Role.INSPECTOR
        session.commit()
    assert auth_client.get("/api/v1/dev/access/admin", headers=token_headers).status_code == 403


def test_password_is_argon2_hash(auth_client):
    with auth_client.app.state.session_factory() as session:
        user = session.scalar(select(User).limit(1))
        assert user.hashed_password.startswith("$argon2id$")
        assert user.hashed_password != auth_client.test_password


def test_no_public_registration(auth_client):
    assert auth_client.post("/api/v1/auth/register").status_code == 404


def test_invalid_request_does_not_echo_password(auth_client):
    password = "private-input-" * 100
    response = auth_client.post("/api/v1/auth/login", json={"email": "admin@labelsure.local", "password": password})
    assert response.status_code == 422
    assert "private-input" not in response.text


def test_dev_routes_absent_in_production():
    settings = Settings(_env_file=None, environment="production", database_url="sqlite://", jwt_secret=secrets.token_urlsafe(48))
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/dev/access/admin").status_code == 404


@pytest.mark.parametrize("kwargs", [{"jwt_secret": "short"}, {"jwt_algorithm": "none"}, {"access_token_expire_minutes": 0}, {"environment": "production", "jwt_secret": None}])
def test_unsafe_config_rejected(kwargs):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **kwargs)


def test_missing_development_secret_fails_closed():
    settings = Settings(_env_file=None, environment="test", database_url="sqlite://", jwt_secret=None)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/auth/login", json={"email": "admin@labelsure.local", "password": "anything"})
        assert response.status_code == 503
