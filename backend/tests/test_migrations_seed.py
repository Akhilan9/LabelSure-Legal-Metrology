from pathlib import Path
import secrets

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.session import build_engine, build_session_factory
from app.models.user import User
from app.scripts.seed_users import seed_users


def test_migration_seed_constraints_and_idempotency(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "auth.db").as_posix()
    monkeypatch.setenv("LABELSURE_DATABASE_URL", url)
    monkeypatch.setenv("LABELSURE_ENVIRONMENT", "development")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    settings = Settings(_env_file=None, environment="development", database_url=url)
    password = secrets.token_urlsafe(24)
    seed_users(settings, lambda role: password)
    engine = build_engine(url)
    try:
        with build_session_factory(engine)() as session:
            before = {u.id: u.hashed_password for u in session.scalars(select(User))}
        assert len(before) == 3
        def must_not_prompt(role):
            raise AssertionError("Existing users must not request passwords")
        seed_users(settings, must_not_prompt)
        with build_session_factory(engine)() as session:
            assert {u.id: u.hashed_password for u in session.scalars(select(User))} == before
        with engine.connect() as connection:
            with pytest.raises(IntegrityError):
                connection.execute(text("UPDATE users SET role='INVALID'"))
            connection.rollback()
        tables = inspect(engine).get_table_names()
        assert "users" in tables
        assert "inspections" in tables
        assert "inspection_images" in tables
    finally:
        engine.dispose()
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_seed_disabled_in_production():
    settings = Settings(_env_file=None, environment="production", jwt_secret=secrets.token_urlsafe(48))
    with pytest.raises(ValueError, match="development"):
        seed_users(settings, lambda role: "unused")
