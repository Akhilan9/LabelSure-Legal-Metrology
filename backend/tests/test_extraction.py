import time
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from test_ocr import client, auth_headers, create_test_image_bytes
from app.extraction.engine import extract
from app.extraction.normalizers import clean, month_year, valid_gtin
from app.extraction.scoring import score
from app.models.ocr import OCRBlock
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.service import set_custom_ocr_provider

def blocks(lines, confidence=.98):
    return [SimpleNamespace(id=str(i), raw_text=text, confidence=confidence,
        bounding_box={"x_min": 20, "x_max": 380, "y_min": i*30, "y_max": i*30+20})
        for i, text in enumerate(lines)]

def candidates(lines, panel="BACK", product=None):
    return extract(blocks(lines), panel, product)

@pytest.mark.parametrize("text", ["MRP ₹120", "MRP: Rs. 120/-", "Maximum Retail Price ₹ 120",
    "M.R.P. Rs 120 Inclusive of all taxes", "MRP: 120/-", "MRP Rs. 1,20/-"])
def test_mrp(text):
    result = candidates([text])
    assert result[0]["normalized_value"] == "120.00"
    assert result[0]["raw_value"] == text

@pytest.mark.parametrize("value,expected", [("500 g","500 g"), ("1 kg","1 kg"), ("250 ml","250 ml"),
    ("2 L","2 L"), ("10 N","10 count"), ("20 pieces","20 count"), ("500 GMS","500 g"),
    ("3 gm","3 g"), ("20 grams","20 g"), ("250 mL","250 ml"), ("2 ltr","2 L"),
    ("2 litre","2 L"), ("2 liters","2 L"), ("3 pcs","3 count")])
def test_quantity(value, expected):
    assert candidates(["Net Qty " + value])[0]["normalized_value"] == expected

@pytest.mark.parametrize("text", ["MFG 08/2026", "Packed on: Aug 2026", "Month & Year of Manufacture: 08/2026"])
def test_dates(text):
    assert candidates([text])[0]["normalized_value"] == "2026-08"

def test_ambiguous_date():
    result = candidates(["PKD: 08-26"])[0]
    assert result["needs_review"]
    assert result["structured_value"]["year"] is None
    assert month_year("13/2026")[1]
    assert month_year("08/09/2026")[1]

@pytest.mark.parametrize("text", ["Country of Origin: India", "Made in India", "Imported from Germany", "Origin: China"])
def test_origin(text):
    result = candidates([text])[0]
    assert result["declaration_type"] == "COUNTRY_OF_ORIGIN"
    assert result["normalized_value"] == text.split()[-1]

@pytest.mark.parametrize("prefix,role", [("Manufactured by:", "MANUFACTURER"), ("Mfd. by", "MANUFACTURER"),
    ("Packed by", "PACKER"), ("Pkd by", "PACKER"), ("Imported by", "IMPORTER"), ("Importer", "IMPORTER")])
def test_organization_address(prefix, role):
    result = candidates([prefix, "ABC Foods Pvt Ltd", "12 Industrial Estate", "Hyderabad 500001", "MRP 120"])
    name = next(c for c in result if c["declaration_type"] == role + "_NAME")
    address = next(c for c in result if c["declaration_type"] == role + "_ADDRESS")
    assert name["normalized_value"] == "ABC Foods Pvt Ltd"
    assert address["normalized_value"] == "12 Industrial Estate Hyderabad 500001"
    assert len(address["sources"]) == 3
    assert address["needs_review"]
    assert "MRP" not in address["raw_value"]

def test_spatial_separation():
    data = blocks(["Manufactured by:", "Unrelated Company"])
    data[1].bounding_box["y_min"] = 1000
    data[1].bounding_box["y_max"] = 1020
    assert extract(data, "BACK") == []

def test_split_label_value():
    result = candidates(["MRP:", "₹120"])
    assert result[0]["normalized_value"] == "120.00"
    assert len(result[0]["sources"]) == 2

def test_consumer_details():
    result = candidates(["Consumer Care:", "APEX Support", "12 Road Hyderabad", "1800-123-4567", "care@example.com"])
    by_type = {c["declaration_type"]: c for c in result}
    assert by_type["CONSUMER_CARE_PHONE"]["normalized_value"] == "18001234567"
    assert by_type["CONSUMER_CARE_EMAIL"]["normalized_value"] == "care@example.com"
    assert by_type["CONSUMER_CARE_NAME"]["normalized_value"] == "APEX Support"
    assert by_type["CONSUMER_CARE_ADDRESS"]["normalized_value"] == "12 Road Hyderabad"

@pytest.mark.parametrize("text", ["120", "500 g", "care@example.com", "ACME Corporation",
    "1234567890123", "Nutrition per 100 g", "Best before 12 months", "hello world",
    "Barcode 1234567890123", "MRP -5", "NET QTY 0 g"])
def test_false_positives(text):
    assert candidates([text]) == []

def test_gtin():
    assert valid_gtin("4006381333931")
    assert not valid_gtin("4006381333932")
    assert candidates(["Barcode: 4006381333931"])[0]["normalized_value"] == "4006381333931"

def test_product_other_and_unit_price():
    assert candidates(["TEST MASALA"], "FRONT") == []
    assert candidates(["TEST MASALA"], "FRONT", "TEST MASALA")[0]["needs_review"]
    assert candidates(["Product name: Masala"])[0]["declaration_type"] == "COMMON_PRODUCT_NAME"
    assert candidates(["Unit sale price Rs 2.50/g"])[0]["normalized_value"] == "2.50/g"
    assert candidates(["Other declaration: Keep dry"])[0]["declaration_type"] == "OTHER"

def test_normalization_scoring_and_untrusted_text():
    raw = "NET\u00a0QTY ５００ GMS"
    assert candidates([raw])[0]["normalized_value"] == "500 g"
    assert candidates([raw])[0]["raw_value"] == raw
    assert clean("a\x00\ud800b") == "a b"
    high, factors = score(blocks(["MRP 120"]), relevant_panel=True)
    low, _ = score(blocks(["MRP 120"], .2), relevant_panel=True)
    assert 0 <= low < high <= 1
    assert high == round(sum(factors.values()), 4)
    assert extract(blocks(["MRP 120"], .2), "BACK")[0]["needs_review"]
    assert candidates(["<script>alert(1)</script>"]) == []

def prepare(client, lines=None):
    headers = auth_headers(client)
    inspection = client.post("/api/v1/inspections", json={"product_name":"LABELSURE TEST MASALA"}, headers=headers).json()
    base = "/api/v1/inspections/" + inspection["id"]
    uploaded = client.post(base + "/images", files=[("files", ("test.jpg", create_test_image_bytes(), "image/jpeg"))],
                          data={"panel_types":["FRONT"]}, headers=headers)
    assert uploaded.status_code == 201
    image_id = uploaded.json()[0]["id"]
    if lines is not None:
        set_custom_ocr_provider(MockOCRProvider(default_blocks=[
            {"raw_text": text, "confidence": .98, "polygon": [[20,i*30],[380,i*30],[380,i*30+20],[20,i*30+20]]}
            for i,text in enumerate(lines)]))
        assert client.post(base + "/images/" + image_id + "/ocr", headers=headers).status_code == 200
    return base, headers, image_id

SYNTHETIC = ["LABELSURE TEST MASALA", "Net Quantity: 500 g", "MRP: ₹120", "(Inclusive of all taxes)",
    "Manufactured by:", "APEX Foods Pvt Ltd", "Hyderabad, Telangana 500001", "Packed: 08/2026",
    "Consumer Care:", "1800-123-4567", "care@example.com", "Country of Origin: India"]

def test_end_to_end_provenance_and_raw_preservation(client):
    base, headers, image_id = prepare(client, SYNTHETIC)
    with client.app.state.session_factory() as db:
        before = {b.id:b.raw_text for b in db.scalars(select(OCRBlock))}
    response = client.post(base + "/extract-declarations", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUCCESS"
    rows = client.get(base + "/declarations", headers=headers).json()
    types = {c["declaration_type"] for c in rows}
    assert {"COMMON_PRODUCT_NAME","MRP","NET_QUANTITY","MANUFACTURER_NAME","MANUFACTURER_ADDRESS",
            "MONTH_YEAR","CONSUMER_CARE_PHONE","CONSUMER_CARE_EMAIL","COUNTRY_OF_ORIGIN"} <= types
    for row in rows:
        assert row["source_image_id"] == image_id
        assert row["sources"]
        assert row["raw_value"] == "\n".join(before[s["ocr_block_id"]] for s in row["sources"])
        assert client.get(base + "/declarations/" + row["id"], headers=headers).json() == row
    with client.app.state.session_factory() as db:
        assert {b.id:b.raw_text for b in db.scalars(select(OCRBlock))} == before
    summary = client.get(base + "/extraction-summary", headers=headers).json()
    assert summary["candidate_count"] == len(rows)

def test_precondition_and_auth(client):
    base, headers, _ = prepare(client)
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 409
    assert client.get(base + "/declarations", headers=headers).json() == []
    for suffix in ["/declarations", "/extraction-summary", "/declarations/missing"]:
        assert client.get(base + suffix).status_code == 401
        assert client.get(base + suffix, headers=auth_headers(client,"inspector2@labelsure.local")).status_code == 404
    assert client.post(base + "/extract-declarations", headers=auth_headers(client,"inspector2@labelsure.local")).status_code == 404
    assert client.post(base + "/extract-declarations", headers=auth_headers(client,"supervisor@labelsure.local")).status_code in {403, 404}

def test_roles_and_candidate_idor(client):
    base, headers, _ = prepare(client, ["MRP 120"])
    admin = auth_headers(client,"admin@labelsure.local")
    supervisor = auth_headers(client,"supervisor@labelsure.local")
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 200
    rows = client.get(base + "/declarations", headers=headers).json()
    assert len(rows) == 1
    assert client.get(base + "/declarations/" + rows[0]["id"], headers=headers).status_code == 200
    other_base, _, _ = prepare(client)
    assert client.get(other_base + "/declarations/" + rows[0]["id"], headers=headers).status_code == 404

def test_idempotency_version_and_new_ocr(client):
    base, headers, image = prepare(client, ["MRP 120"])
    first = client.post(base + "/extract-declarations", headers=headers).json()
    assert client.post(base + "/extract-declarations", headers=headers).json()["id"] == first["id"]
    client.app.state.settings.extraction_pipeline_version = "2"
    second = client.post(base + "/extract-declarations", headers=headers).json()
    assert second["id"] != first["id"]
    assert second["version"] == "2"
    assert client.post(base + "/images/" + image + "/ocr?force=true", headers=headers).status_code == 200
    assert client.get(base + "/extraction-summary", headers=headers).json()["run"] is None
    assert client.post(base + "/extract-declarations", headers=headers).json()["id"] != second["id"]

@pytest.mark.parametrize("values,conflict", [(["MRP 120","MRP 120"],False), (["MRP 120","MRP 125"],True)])
def test_duplicates_and_conflicts(client, values, conflict):
    base, headers, _ = prepare(client, values)
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 200
    rows = client.get(base + "/declarations", headers=headers).json()
    assert len(rows) == 2
    assert len({r["source_ocr_block_id"] for r in rows}) == 2
    assert sum(r["is_primary"] for r in rows) == (0 if conflict else 1)
    if conflict:
        assert all(r["needs_review"] and "Conflicting candidates" in r["review_reasons"] for r in rows)

def test_payload_limit(client):
    base, headers, _ = prepare(client, ["MRP 120 " + "x"*2100])
    response = client.post(base + "/extract-declarations", headers=headers)
    assert response.status_code == 422

def test_bounded_performance():
    data = blocks(["Unrelated package text"] * 1000)
    started = time.perf_counter()
    assert extract(data,"BACK") == []
    assert time.perf_counter() - started < 3


def test_latest_failed_ocr_does_not_reuse_old_candidates(client):
    base, headers, image = prepare(client, ["MRP 120"])
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 200
    set_custom_ocr_provider(MockOCRProvider(simulate_failure=True))
    assert client.post(base + "/images/" + image + "/ocr?force=true", headers=headers).status_code == 200
    assert client.get(base + "/declarations", headers=headers).json() == []
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 409

def test_panel_duplicates_and_partial_evidence(client):
    base, headers, first_image = prepare(client, ["MRP 120"])
    second = client.post(base + "/images", files=[("files",("back.jpg",create_test_image_bytes(),"image/jpeg"))],
                        data={"panel_types":["BACK"]}, headers=headers)
    assert second.status_code == 201
    assert client.post(base + "/extract-declarations", headers=headers).json()["status"] == "PARTIAL"
    image = second.json()[0]["id"]
    assert client.post(base + "/images/" + image + "/ocr", headers=headers).status_code == 200
    assert client.post(base + "/extract-declarations", headers=headers).json()["status"] == "SUCCESS"
    rows = client.get(base + "/declarations", headers=headers).json()
    assert len(rows) == 2
    assert {r["source_image_id"] for r in rows} == {first_image,image}
    assert {r["panel_type"] for r in rows} == {"FRONT","BACK"}
    assert sum(r["is_primary"] for r in rows) == 1

def test_extraction_does_not_change_inspection_status(client):
    base, headers, _ = prepare(client, ["MRP 120"])
    before = client.get(base,headers=headers).json()["status"]
    client.post(base + "/extract-declarations",headers=headers)
    assert client.get(base,headers=headers).json()["status"] == before


def test_photo_first_autofill_remains_discoverable(client):
    base, headers, _ = prepare(client, ["Product Name: Roasted Almonds", "Manufactured by: APEX Foods"])
    assert client.patch(base, json={"product_name": ""}, headers=headers).status_code == 200
    result = client.post(base + "/extract-declarations", headers=headers)
    assert result.status_code == 200, result.text
    details = client.get(base, headers=headers).json()
    assert details["product_name"] == "Roasted Almonds"
    assert details["manufacturer_name"] == "APEX Foods"
    assert client.get(base + "/declarations", headers=headers).json()
    assert client.post(base + "/extract-declarations", headers=headers).json()["id"] == result.json()["id"]


def test_conflicting_names_do_not_autofill(client):
    base, headers, _ = prepare(client, ["Manufactured by: First Foods", "Manufactured by: Second Foods"])
    result = client.post(base + "/extract-declarations", headers=headers)
    assert result.status_code == 200, result.text
    assert not client.get(base, headers=headers).json()["manufacturer_name"]


def test_autofill_preserves_inspector_corrections(client):
    base, headers, _ = prepare(client, ["Manufactured by: Scanned Foods"])
    client.patch(base, json={"manufacturer_name": "Corrected Foods"}, headers=headers)
    assert client.post(base + "/extract-declarations", headers=headers).status_code == 200
    assert client.get(base, headers=headers).json()["manufacturer_name"] == "Corrected Foods"
