import pytest
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC
from app.rules.loader import load_ruleset
from app.rules.explainability import explain_result
from tests.test_rules import mock_snapshot


def test_explain_result_pass():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()

    mock_result = {
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "rule_version": "1",
        "title": "Maximum Retail Price (MRP) Statutory Declaration",
        "legal_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "legal_status": "PROTOTYPE_RULE",
        "severity": "CRITICAL",
        "verdict": "PASS",
        "reason_code": "DECLARATION_VALID",
        "explanation": "Valid MRP declaration detected and verified.",
        "applicability_state": "APPLICABLE",
        "evidence_confidence": 0.95,
        "rule_definition": rule.model_dump(mode="json"),
        "evidence": [
            {"declaration_candidate_id": "cand-mrp", "context_fact_id": None, "inspection_image_id": "img-1"}
        ]
    }

    explanation = explain_result(mock_result, {}, snap)
    assert explanation["rule_key"] == "MRP_PRESENCE"
    assert explanation["verdict"] == "PASS"
    assert len(explanation["decision_trace"]) >= 4
    assert explanation["decision_trace"][0]["status"] == "PASSED"
    assert "Statutory requirement is satisfied" in explanation["counterfactual_guidance"]
    assert len(explanation["linked_evidence"]["declarations"]) == 1
    assert explanation["linked_evidence"]["declarations"][0]["id"] == "cand-mrp"


def test_explain_result_fail_absence():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()
    snap["declarations"] = []

    mock_result = {
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "rule_version": "1",
        "title": "Maximum Retail Price (MRP) Statutory Declaration",
        "legal_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "legal_status": "PROTOTYPE_RULE",
        "severity": "CRITICAL",
        "verdict": "FAIL",
        "reason_code": "DECLARATION_NOT_DETECTED",
        "explanation": "Mandatory MRP declaration was not detected on readable package panels.",
        "applicability_state": "APPLICABLE",
        "evidence_confidence": 0.95,
        "rule_definition": rule.model_dump(mode="json"),
        "evidence": []
    }

    explanation = explain_result(mock_result, {}, snap)
    assert explanation["verdict"] == "FAIL"
    assert explanation["reason_code"] == "DECLARATION_NOT_DETECTED"
    violation_step = next(s for s in explanation["decision_trace"] if s["phase"] == "DECLARATION_DETECTION")
    assert violation_step["status"] == "VIOLATION"
    assert "Ensure the mandatory declaration is printed prominently" in explanation["counterfactual_guidance"]


def test_explain_result_uncertain_ocr_failed():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()
    snap["declarations"] = []

    mock_result = {
        "rule_id": "DEMO-MRP_PRESENCE",
        "rule_key": "MRP_PRESENCE",
        "rule_version": "1",
        "title": "Maximum Retail Price (MRP) Statutory Declaration",
        "legal_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "legal_status": "PROTOTYPE_RULE",
        "severity": "CRITICAL",
        "verdict": "UNCERTAIN",
        "reason_code": "OCR_FAILED",
        "explanation": "OCR processing failed on one or more panels.",
        "applicability_state": "APPLICABLE",
        "evidence_confidence": None,
        "rule_definition": rule.model_dump(mode="json"),
        "evidence": []
    }

    explanation = explain_result(mock_result, {}, snap)
    assert explanation["verdict"] == "UNCERTAIN"
    assert explanation["reason_code"] == "OCR_FAILED"
    sufficiency_step = next(s for s in explanation["decision_trace"] if s["phase"] == "EVIDENCE_SUFFICIENCY")
    assert sufficiency_step["status"] == "FAILED"
    assert "Re-capture clear, well-lit photo" in explanation["counterfactual_guidance"]


def test_rulelens_api_endpoints(client):
    base, user_h, _ = prepare(client, SYNTHETIC)

    client.post(base + "/extract-declarations", headers=user_h).raise_for_status()
    client.post(base + "/resolve-context", json={"inspector_input": {"import_status": "DOMESTIC", "package_type": "POUCH", "product_category": "FOOD"}}, headers=user_h).raise_for_status()
    client.post(base + "/evaluate", headers=user_h, json={"allow_prototype_rules": True}).raise_for_status()

    # 1. Single explanation by key
    expl_res = client.get(base + "/rules/MRP_PRESENCE/explanation", headers=user_h)
    assert expl_res.status_code == 200
    expl = expl_res.json()
    assert expl["rule_key"] == "MRP_PRESENCE"
    assert "decision_trace" in expl
    assert "counterfactual_guidance" in expl
    assert "linked_evidence" in expl

    # 2. All explanations
    all_expl_res = client.get(base + "/rules/explanations", headers=user_h)
    assert all_expl_res.status_code == 200
    all_expl = all_expl_res.json()
    assert len(all_expl) >= 4
    assert any(e["rule_key"] == "MRP_PRESENCE" for e in all_expl)
