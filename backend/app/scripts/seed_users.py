import argparse
import getpass
import os

from sqlalchemy import select

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import build_engine, build_session_factory
from app.models.user import Role, User


def seed_users(settings, password_provider, reset=False):
    if settings.environment != "development":
        raise ValueError("Seeding is permitted only in development")
    engine = build_engine(settings.database_url)
    try:
        with build_session_factory(engine)() as session:
            for role in Role:
                email = f"{role.value.lower()}@labelsure.local"
                user = session.scalar(select(User).where(User.email == email))
                if user and not reset:
                    print(f"Preserved existing user: {email}")
                    continue
                password = password_provider(role)
                if len(password) < 12 or len(password) > 1024:
                    raise ValueError("Seed passwords must have 12 to 1024 characters")
                if user:
                    user.hashed_password = hash_password(password)
                else:
                    session.add(User(full_name=f"Local {role.value.title()}", email=email,
                                     role=role, hashed_password=hash_password(password)))
                print(f"Prepared development user: {email}")
            session.commit()
        print("Development users saved. Existing roles and active states are never changed.")
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Seed local users after alembic upgrade head")
    parser.add_argument("--reset-passwords", action="store_true", help="Explicitly replace existing seed-user passwords")
    args = parser.parse_args()
    # Settings loads application config; seed secrets can come from process env or local .env.
    from dotenv import dotenv_values
    values = dotenv_values(".env")

    def password_provider(role):
        key = f"LABELSURE_SEED_{role.value}_PASSWORD"
        password = os.environ.get(key) or values.get(key)
        if password:
            return password
        password = getpass.getpass(f"Password for {role.value.lower()}@labelsure.local (12+ characters): ")
        if password != getpass.getpass("Confirm password: "):
            raise ValueError("Passwords do not match")
        return password

    try:
        seed_users(Settings(), password_provider, reset=args.reset_passwords)
    except ValueError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
