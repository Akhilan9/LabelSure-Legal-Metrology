import io
import pytest
from PIL import Image
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC


def test_security_headers_present_on_api_responses(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_cross_inspector_idor_isolation_across_subresources(client):
    # Inspector 1 creates inspection
    base1, user1_h, _ = prepare(client, SYNTHETIC)
    insp1_id = base1.split("/")[-1]

    # Inspector 2 credentials
    user2_h = auth_headers(client, "inspector2@labelsure.local")

    # Inspector 2 cannot view or execute actions on Inspector 1's inspection (rejected with 403 or 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/ocr/summary", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/declarations", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/context", headers=user2_h).status_code in (403, 404)
    assert client.post(f"/api/v1/inspections/{insp1_id}/evaluate", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/evaluation", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/review", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/reports/summary", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/reports/pdf", headers=user2_h).status_code in (403, 404)
    assert client.get(f"/api/v1/inspections/{insp1_id}/reports/csv", headers=user2_h).status_code in (403, 404)


def test_image_decompression_bomb_defense():
    from app.image_processing.preprocessing import ImagePreprocessor

    # Verify PIL.Image.MAX_IMAGE_PIXELS is set to a secure bound
    assert Image.MAX_IMAGE_PIXELS <= 50_000_000

    # Ensure empty bytes raise ValueError gracefully
    with pytest.raises(ValueError, match="empty"):
        ImagePreprocessor.decode_and_orient(b"")


def test_cors_policy_strictness(client):
    # Allowed origin succeeds
    resp = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    })
    assert resp.status_code == 200

    # Disallowed untrusted origin rejected
    resp_bad = client.options("/api/v1/health", headers={
        "Origin": "http://malicious-site.com",
        "Access-Control-Request-Method": "GET"
    })
    assert "access-control-allow-origin" not in resp_bad.headers
