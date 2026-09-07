import pytest
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC
from app.reports.exporter import sanitize_csv_cell, compute_sha256


def test_csv_formula_injection_defense():
    # Verify formula injection strings are prefixed with single quote
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert sanitize_csv_cell("+100") == "'+100"
    assert sanitize_csv_cell("-50") == "'-50"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\t=1+1") == "'\t=1+1"
    assert sanitize_csv_cell("%0A1") == "'%0A1"

    # Benign text should remain unmodified
    assert sanitize_csv_cell("MRP 120.00") == "MRP 120.00"
    assert sanitize_csv_cell("Net Quantity: 500 g") == "Net Quantity: 500 g"
    assert sanitize_csv_cell(120) == "120"
    assert sanitize_csv_cell(None) == ""


def test_report_generation_end_to_end(client):
    base, user_h, _ = prepare(client, SYNTHETIC)
    admin_h = auth_headers(client, "admin@labelsure.local")
    sup_h = auth_headers(client, "supervisor@labelsure.local")

    # Pipeline up to rule evaluation and human review
    client.post(base + "/extract-declarations", headers=user_h).raise_for_status()
    client.post(base + "/resolve-context", json={"inspector_input": {"import_status": "DOMESTIC", "package_type": "POUCH", "product_category": "FOOD"}}, headers=user_h).raise_for_status()
    client.post(base + "/evaluate", headers=user_h, json={"allow_prototype_rules": True}).raise_for_status()

    # Rule decision
    client.post(base + "/review/rule-decisions", headers=user_h, json={
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "final_verdict": "PASS",
        "reviewer_notes": "Inspector verified physical presence."
    }).raise_for_status()

    # Finalize review
    client.post(base + "/review/finalize", headers=user_h, json={
        "final_compliance_status": "COMPLIANT",
        "summary_notes": "Complete packaged commodity compliance verified."
    }).raise_for_status()

    # 1. Summary Report JSON API
    summary_res = client.get(base + "/reports/summary", headers=user_h)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["overall_compliance"] == "COMPLIANT"
    assert summary["is_finalized"] is True
    assert summary["pass_count"] >= 1
    assert len(summary["tamper_sha256"]) == 64
    assert len(summary["rule_evaluations"]) >= 1

    # 2. PDF Report Generation & Download
    pdf_res = client.get(base + "/reports/pdf", headers=user_h)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    pdf_bytes = pdf_res.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # 3. CSV Rules & Violations Export
    csv_rules_res = client.get(base + "/reports/csv?target=rules", headers=user_h)
    assert csv_rules_res.status_code == 200
    assert "text/csv" in csv_rules_res.headers["content-type"]
    csv_text = csv_rules_res.text
    assert "LabelSure Legal Metrology Compliance" in csv_text
    assert "MRP_PRESENCE" in csv_text
    assert "COMPLIANT" in csv_text

    # 4. CSV Declarations Ledger Export
    csv_decl_res = client.get(base + "/reports/csv?target=declarations", headers=user_h)
    assert csv_decl_res.status_code == 200
    assert "LabelSure Declaration Candidates" in csv_decl_res.text
    assert "MRP" in csv_decl_res.text

    # 5. Full JSON Snapshot Export
    json_res = client.get(base + "/reports/json", headers=user_h)
    assert json_res.status_code == 200
    assert "application/json" in json_res.headers["content-type"]
    json_data = json_res.json()
    assert json_data["inspection_id"] == base.split("/")[-1]
    assert json_data["overall_compliance"] == "COMPLIANT"
    assert len(json_data["tamper_sha256"]) == 64

    # 6. Supervisor & Admin Access
    assert client.get(base + "/reports/summary", headers=sup_h).status_code == 200
    assert client.get(base + "/reports/pdf", headers=admin_h).status_code == 200
