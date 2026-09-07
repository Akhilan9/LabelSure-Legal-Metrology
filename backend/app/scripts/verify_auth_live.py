"""Exercise real HTTP authentication against an isolated, disposable local database."""
from pathlib import Path
import os
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx


def main():
    root = Path(__file__).resolve().parents[2]
    database = (root / f"verify-auth-{uuid4().hex}.db").resolve()
    if database.parent != root.resolve():
        raise RuntimeError("Verification database must remain within backend")
    env = os.environ.copy()
    env.update(LABELSURE_ENVIRONMENT="development", LABELSURE_DATABASE_URL="sqlite:///" + database.as_posix(),
               JWT_SECRET=secrets.token_urlsafe(48), JWT_ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES="30")
    passwords = {role: secrets.token_urlsafe(24) for role in ("ADMIN", "INSPECTOR", "SUPERVISOR")}
    env.update({f"LABELSURE_SEED_{role}_PASSWORD": password for role, password in passwords.items()})
    process = None
    try:
        for module, args in [("alembic", ["upgrade", "head"]), ("app.scripts.seed_users", [])]:
            subprocess.run([sys.executable, "-m", module, *args], cwd=root, env=env, check=True)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        # No passwords or tokens are emitted. Child lifetime is owned by this script.
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                                   cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}/api/v1", timeout=3) as client:
            for attempt in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Verification server exited before readiness")
                try:
                    response = client.get("/health")
                    if response.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("Verification API did not become ready")
            assert response.json()["database"] == "connected"
            print("GET /api/v1/health: 200, database connected")
            for role, password in passwords.items():
                response = client.post("/auth/login", json={"email": f"{role.lower()}@labelsure.local", "password": password})
                assert response.status_code == 200
                assert response.json()["user"]["role"] == role
                auth = {"Authorization": "Bearer " + response.json()["access_token"]}
                assert client.get("/auth/me", headers=auth).json()["role"] == role
                for endpoint, allowed in {"admin": {"ADMIN"}, "inspection": {"ADMIN", "INSPECTOR"}, "monitoring": {"ADMIN", "SUPERVISOR"}}.items():
                    expected = 200 if role in allowed else 403
                    assert client.get(f"/dev/access/{endpoint}", headers=auth).status_code == expected
                print(f"{role}: login 200, /auth/me 200, RBAC matrix passed")
            assert client.get("/auth/me").status_code == 401
            assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
            assert client.post("/auth/login", json={"email": "admin@labelsure.local", "password": "incorrect"}).status_code == 401
            print("Missing token, invalid token and incorrect password: 401")
        print("Live Phase 2 HTTP verification passed.")
    finally:
        if process:
            if os.name == "nt" and process.poll() is None:
                # Windows venv launchers can spawn another Python executable.
                # Stop only this script's owned process tree, not servers by name/port.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        database.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
