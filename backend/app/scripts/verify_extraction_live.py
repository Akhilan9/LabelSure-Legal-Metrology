"""Controlled loopback HTTP verification; never touches the user's database."""
import json
import secrets
import socket
import tempfile
import threading
import time
from pathlib import Path
import cv2
import httpx
import numpy as np
import uvicorn
from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base, build_engine, build_session_factory
from app.main import create_app
from app.models.user import User, Role
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.service import set_custom_ocr_provider

TEXT = ["LABELSURE TEST MASALA", "Net Quantity: 500 g", "MRP: ₹120",
        "(Inclusive of all taxes)", "Manufactured by:", "APEX Foods Pvt Ltd",
        "Hyderabad, Telangana 500001", "Packed: 08/2026", "Consumer Care:",
        "1800-123-4567", "care@example.com", "Country of Origin: India"]

def main():
    with tempfile.TemporaryDirectory(prefix="labelsure-phase6-") as tmp:
        settings = Settings(_env_file=None, environment="test",
            database_url="sqlite:///" + (Path(tmp) / "test.db").as_posix(),
            storage_local_dir=str(Path(tmp) / "storage"), jwt_secret=secrets.token_urlsafe(48), ocr_provider="mock")
        engine = build_engine(settings.database_url)
        Base.metadata.create_all(engine)
        password = secrets.token_urlsafe(24)
        with build_session_factory(engine)() as db:
            db.add(User(id="live-inspector", email="live@example.test", full_name="Controlled verification",
                        hashed_password=hash_password(password), role=Role.INSPECTOR))
            db.commit()
        engine.dispose()
        set_custom_ocr_provider(MockOCRProvider(default_blocks=[
            {"raw_text": value, "confidence": .98,
             "polygon": [[20,i*40+10],[600,i*40+10],[600,i*40+35],[20,i*40+35]]}
            for i,value in enumerate(TEXT)]))
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets":[sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started and time.monotonic() < deadline:
                time.sleep(.05)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{port}/api/v1", timeout=30) as client:
                login = client.post("/auth/login", json={"email":"live@example.test","password":password})
                login.raise_for_status()
                client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
                inspection = client.post("/inspections", json={"product_name":TEXT[0]})
                inspection.raise_for_status()
                base = "/inspections/" + inspection.json()["id"]
                img = np.full((800,800,3),255,dtype=np.uint8)
                for i,line in enumerate(TEXT):
                    cv2.putText(img,line.replace("₹","Rs."),(20,i*40+30),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,0),1)
                _, encoded = cv2.imencode(".png",img)
                upload = client.post(base+"/images",files=[("files",("synthetic.png",encoded.tobytes(),"image/png"))],data={"panel_types":"FRONT"})
                upload.raise_for_status()
                image = upload.json()[0]["id"]
                ocr = client.post(base+"/images/"+image+"/ocr")
                ocr.raise_for_status()
                started = time.perf_counter()
                extraction = client.post(base+"/extract-declarations")
                extraction.raise_for_status()
                duration = time.perf_counter() - started
                rows = client.get(base+"/declarations").json()
                types = sorted({c["declaration_type"] for c in rows})
                expected = {"COMMON_PRODUCT_NAME","NET_QUANTITY","MRP","MANUFACTURER_NAME",
                            "MANUFACTURER_ADDRESS","MONTH_YEAR","CONSUMER_CARE_PHONE","CONSUMER_CARE_EMAIL","COUNTRY_OF_ORIGIN"}
                assert expected <= set(types), types
                assert all(c["sources"] for c in rows)
                assert client.get(base+"/images/"+image+"/content").status_code == 200
                assert client.get(base+"/declarations/"+rows[0]["id"]).status_code == 200
                assert client.post(base+"/extract-declarations").json()["id"] == extraction.json()["id"]
                print(json.dumps({"transport":"loopback HTTP","ocr":"controlled deterministic fixture",
                    "status":extraction.json()["status"],"candidate_count":len(rows),"types":types,
                    "extraction_http_ms":round(duration*1000,2),"provenance":True,"idempotency":True},indent=2))
        finally:
            server.should_exit = True
            thread.join(timeout=15)
            sock.close()
            set_custom_ocr_provider(None)
            assert not thread.is_alive()

if __name__ == "__main__":
    main()

