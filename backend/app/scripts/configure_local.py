from pathlib import Path
import secrets

from dotenv import dotenv_values

from app.core.config import Settings


def main():
    settings = Settings()
    if settings.environment != "development":
        raise SystemExit("Local setup is available only in development.")
    if settings.jwt_secret:
        print("JWT configuration already present; preserved.")
        return
    path = Path(".env")
    values = dotenv_values(path) if path.exists() else {}
    if "JWT_SECRET" in values:
        raise SystemExit("An existing JWT_SECRET entry requires manual correction; no values replaced.")
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\nJWT_SECRET=" + secrets.token_urlsafe(48) + "\n")
    print("Generated JWT_SECRET in backend/.env. Value is not printed. Keep this file private.")


if __name__ == "__main__":
    main()
