import pytest
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC


def test_human_review_end_to_end_flow(client):
    base, user_h, _ = prepare(client, SYNTHETIC)
    admin_h = auth_headers(client, "admin@labelsure.local")
    sup_h = auth_headers(client, "supervisor@labelsure.local")

    # Pipeline up to rule evaluation
    client.post(base + "/extract-declarations", headers=user_h).raise_for_status()
    client.post(base + "/resolve-context", json={"inspector_input": {"import_status": "DOMESTIC", "package_type": "POUCH", "product_category": "FOOD"}}, headers=user_h).raise_for_status()
    client.post(base + "/evaluate", headers=user_h, json={"allow_prototype_rules": True}).raise_for_status()

    # 1. Get or create review session
    review_res = client.get(base + "/review", headers=user_h)
    assert review_res.status_code == 200
    review = review_res.json()
    assert review["status"] == "DRAFT"
    assert review["inspection_id"] == base.split("/")[-1]

    # 2. Rule decision: Confirm matching verdict (PASS -> PASS)
    dec1_res = client.post(base + "/review/rule-decisions", headers=user_h, json={
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "final_verdict": "PASS",
        "reviewer_notes": "Verified authentic printed declaration on front panel."
    })
    assert dec1_res.status_code == 200
    assert dec1_res.json()["is_overridden"] is False

    # 3. Rule override: Override verdict without required reason -> 422
    invalid_override = client.post(base + "/review/rule-decisions", headers=user_h, json={
        "rule_id": "DEMO-NET_QUANTITY_STRUCTURE",
        "rule_key": "NET_QUANTITY_STRUCTURE",
        "final_verdict": "FAIL",
        "override_reason": ""
    })
    assert invalid_override.status_code == 422

    # 4. Rule override: Override verdict with valid reason -> 200
    valid_override = client.post(base + "/review/rule-decisions", headers=user_h, json={
        "rule_id": "DEMO-NET_QUANTITY_STRUCTURE",
        "rule_key": "NET_QUANTITY_STRUCTURE",
        "final_verdict": "FAIL",
        "override_reason": "Font height is below statutory 2mm minimum requirement per Rule 9."
    })
    assert valid_override.status_code == 200
    assert valid_override.json()["is_overridden"] is True
    assert "Rule 9" in valid_override.json()["override_reason"]

    # 5. Declaration Correction
    decl_corr = client.post(base + "/review/declaration-corrections", headers=user_h, json={
        "declaration_type": "MRP",
        "original_raw_value": "MRP ₹120",
        "original_normalized_value": "120.00",
        "corrected_value": "INR 120.00 (Incl. of all taxes)",
        "action": "CORRECTED",
        "correction_reason": "Added explicit tax inclusion clause per statutory guideline."
    })
    assert decl_corr.status_code == 200
    assert decl_corr.json()["action"] == "CORRECTED"

    # 6. OCR Correction
    ocr_corr = client.post(base + "/review/ocr-corrections", headers=user_h, json={
        "original_text": "Net Quantity: 500 g",
        "corrected_text": "Net Quantity: 500 g",
        "action": "CONFIRMED",
        "correction_reason": "Inspector confirmed OCR character recognition accuracy."
    })
    assert ocr_corr.status_code == 200

    # 7. Finalize review
    finalize_res = client.post(base + "/review/finalize", headers=user_h, json={
        "final_compliance_status": "NON_COMPLIANT",
        "summary_notes": "Inspection completed. Net quantity declaration violates font size mandate."
    })
    assert finalize_res.status_code == 200
    assert finalize_res.json()["status"] == "FINALIZED"
    assert finalize_res.json()["final_compliance_status"] == "NON_COMPLIANT"

    # 8. Modifying a finalized review returns 409 Conflict
    blocked_edit = client.post(base + "/review/rule-decisions", headers=user_h, json={
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "final_verdict": "FAIL",
        "override_reason": "Attempted post-finalization edit."
    })
    assert blocked_edit.status_code == 409

    # 9. Non-admin cannot reopen -> 403
    sup_reopen = client.post(base + "/review/reopen", headers=sup_h, json={
        "reopen_reason": "Supervisor requesting review update"
    })
    assert sup_reopen.status_code == 403

    user_reopen = client.post(base + "/review/reopen", headers=user_h, json={
        "reopen_reason": "Inspector requesting review update"
    })
    assert user_reopen.status_code == 403

    # 10. Admin can reopen with justification -> 200
    admin_reopen = client.post(base + "/review/reopen", headers=admin_h, json={
        "reopen_reason": "Legal appeals board requested re-verification of label panel."
    })
    assert admin_reopen.status_code == 200
    assert admin_reopen.json()["status"] == "REOPENED"

    # 11. Audit Trail verification
    audit_res = client.get(base + "/audit-trail", headers=user_h)
    assert audit_res.status_code == 200
    events = audit_res.json()
    actions = [e["action"] for e in events]
    assert "REVIEW_CREATED" in actions
    assert "RULE_OVERRIDE" in actions
    assert "DECLARATION_CORRECTED" in actions
    assert "REVIEW_FINALIZED" in actions
    assert "REVIEW_REOPENED" in actions
