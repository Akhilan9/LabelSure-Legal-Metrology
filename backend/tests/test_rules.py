import copy
from datetime import date
import pytest
from sqlalchemy import select
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC
from app.context.service import digest
from app.rules.schemas import RuleSet, RuleDefinition
from app.rules.loader import load_ruleset, parse_ruleset
from app.rules.registry import RuleRegistry
from app.rules.conditions import condition, validate_condition
from app.rules.evaluator import evaluate_rule, aggregate
from app.models.rules import RuleEvaluationRun, RuleEvaluationResult, RuleEvaluationEvidence
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.service import set_custom_ocr_provider

def mock_snapshot():
    return {
        "id": "snap-123",
        "created_at": "2026-09-01T10:00:00Z",
        "content_sha256": "a" * 64,
        "context_keys": {
            "package.type": {"state": "KNOWN", "value": "POUCH", "fact_ids": ["f1"]},
            "package.import_status": {"state": "KNOWN", "value": "DOMESTIC", "fact_ids": ["f2"]},
            "evidence.sufficiency": {"state": "KNOWN", "value": "SUFFICIENT_FOR_RULE_EVALUATION", "fact_ids": []}
        },
        "facts": [
            {"id": "f1", "fact_type": "PACKAGE_TYPE", "value": "POUCH"},
            {"id": "f2", "fact_type": "IMPORT_STATUS", "value": "DOMESTIC"}
        ],
        "declarations": [
            {
                "id": "cand-mrp",
                "declaration_type": "MRP",
                "normalized_value": "INR 120.00",
                "confidence_score": 0.95,
                "source_image_id": "img-1",
                "needs_review": False,
                "review_reasons": [],
                "structured_value": {"numeric_value": 120, "currency": "INR"},
                "sources": [{"ocr_block_id": "blk-1", "sequence_order": 0}]
            },
            {
                "id": "cand-netqty",
                "declaration_type": "NET_QUANTITY",
                "normalized_value": "500 g",
                "confidence_score": 0.94,
                "source_image_id": "img-1",
                "needs_review": False,
                "review_reasons": [],
                "structured_value": {"numeric_value": "500", "unit": "g"},
                "sources": [{"ocr_block_id": "blk-2", "sequence_order": 0}]
            },
            {
                "id": "cand-mfg",
                "declaration_type": "MONTH_YEAR",
                "normalized_value": "08/2026",
                "confidence_score": 0.92,
                "source_image_id": "img-1",
                "needs_review": False,
                "review_reasons": [],
                "structured_value": {"month": 8, "year": 2026},
                "sources": [{"ocr_block_id": "blk-3", "sequence_order": 0}]
            },
            {
                "id": "cand-care",
                "declaration_type": "CONSUMER_CARE_PHONE",
                "normalized_value": "1800112233",
                "confidence_score": 0.91,
                "source_image_id": "img-1",
                "needs_review": False,
                "review_reasons": [],
                "structured_value": {},
                "sources": [{"ocr_block_id": "blk-4", "sequence_order": 0}]
            }
        ],
        "evidence": {"state": "SUFFICIENT"},
        "source_inputs": {
            "extraction_run_id": "ext-1",
            "extraction_status": "SUCCESS",
            "images": [{"id": "img-1", "panel": "DECLARATION_PANEL", "quality": "GOOD"}],
            "ocr": [{"id": "ocr-1", "image_id": "img-1", "status": "SUCCESS", "block_count": 10, "confidence": 0.96}]
        }
    }

def test_rule_loading_and_registry():
    ruleset = load_ruleset("labelsure_prototype", "1")
    assert ruleset.ruleset_id == "labelsure_prototype"
    assert len(ruleset.rules) >= 4
    registry = RuleRegistry(ruleset)
    assert "DEMO-MRP_PRESENCE" in registry.by_id
    active, skipped = registry.select(date(2026, 9, 1), allow_prototypes=True)
    assert len(active) >= 4
    # Without prototype allow, prototype rules should be skipped with PROTOTYPE_OPT_IN_REQUIRED or DISABLED
    active_no_proto, skipped_proto = registry.select(date(2026, 9, 1), allow_prototypes=False)
    assert len(active_no_proto) == 0
    assert all(s["reason"] in {"PROTOTYPE_OPT_IN_REQUIRED", "DISABLED"} for s in skipped_proto)

def test_condition_dsl_operators():
    keys = {
        "package.import_status": {"state": "KNOWN", "value": "IMPORTED"},
        "package.type": {"state": "KNOWN", "value": "POUCH"},
        "product.category": {"state": "KNOWN", "value": "FOOD"}
    }
    assert condition({"key": "package.import_status", "operator": "equals", "value": "IMPORTED"}, keys) is True
    assert condition({"key": "package.import_status", "operator": "equals", "value": "DOMESTIC"}, keys) is False
    assert condition({"key": "package.import_status", "operator": "not_equals", "value": "DOMESTIC"}, keys) is True
    assert condition({"key": "package.type", "operator": "in", "value": ["POUCH", "BOX"]}, keys) is True
    assert condition({"key": "package.type", "operator": "not_in", "value": ["CAN", "BOTTLE"]}, keys) is True
    assert condition({"key": "package.type", "operator": "exists"}, keys) is True
    assert condition({"key": "quantity.kind", "operator": "exists"}, keys) is None

    # Group condition
    all_cond = {"all": [
        {"key": "package.import_status", "operator": "equals", "value": "IMPORTED"},
        {"key": "package.type", "operator": "equals", "value": "POUCH"}
    ]}
    assert condition(all_cond, keys) is True

def test_condition_validation_rejects_malicious_or_unknown():
    with pytest.raises(ValueError):
        validate_condition({"key": "unknown.key", "operator": "equals", "value": "X"})
    with pytest.raises(ValueError):
        validate_condition({"key": "package.type", "operator": "eval", "value": "print(1)"})
    with pytest.raises(ValueError):
        validate_condition({"key": "package.type", "operator": "exists", "value": "extra"})

def test_critical_semantic_case_1_ocr_failed_is_uncertain_never_fail():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()
    snap["declarations"] = []
    snap["source_inputs"]["ocr"][0]["status"] = "FAILED"
    res = evaluate_rule(rule, snap)
    assert res["verdict"] == "UNCERTAIN"
    assert res["reason_code"] == "OCR_FAILED"

def test_critical_semantic_case_2_importer_domestic_is_not_applicable():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "IMPORTER_PRESENCE")
    snap = mock_snapshot()
    snap["context_keys"]["package.import_status"]["value"] = "DOMESTIC"
    res = evaluate_rule(rule, snap)
    assert res["verdict"] == "NOT_APPLICABLE"
    assert res["reason_code"] == "RULE_NOT_APPLICABLE"

def test_critical_semantic_case_3_importer_unknown_context_is_uncertain():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "IMPORTER_PRESENCE")
    snap = mock_snapshot()
    snap["context_keys"]["package.import_status"]["state"] = "UNKNOWN"
    snap["context_keys"]["package.import_status"]["value"] = "UNKNOWN"
    res = evaluate_rule(rule, snap)
    assert res["verdict"] == "UNCERTAIN"
    assert res["reason_code"] == "CONTEXT_UNKNOWN"

def test_critical_semantic_case_4_conflicting_candidates_is_uncertain():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()
    cand1 = copy.deepcopy(snap["declarations"][0])
    cand1["id"] = "mrp-1"
    cand1["normalized_value"] = "INR 120.00"
    cand2 = copy.deepcopy(snap["declarations"][0])
    cand2["id"] = "mrp-2"
    cand2["normalized_value"] = "INR 130.00"
    snap["declarations"] = [cand1, cand2]
    res = evaluate_rule(rule, snap)
    assert res["verdict"] == "UNCERTAIN"
    assert res["reason_code"] == "CONFLICTING_CANDIDATES"

def test_critical_semantic_case_5_absence_with_strong_evidence_is_fail():
    ruleset = load_ruleset("labelsure_prototype", "1")
    rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    snap = mock_snapshot()
    snap["declarations"] = []
    snap["source_inputs"]["images"] = [{"id": "img-1", "panel": "DECLARATION_PANEL", "quality": "GOOD"}]
    snap["source_inputs"]["ocr"] = [{"id": "ocr-1", "image_id": "img-1", "status": "SUCCESS", "block_count": 10, "confidence": 0.95}]
    res = evaluate_rule(rule, snap)
    assert res["verdict"] == "FAIL"
    assert res["reason_code"] == "DECLARATION_NOT_DETECTED"

def test_pass_scenarios():
    ruleset = load_ruleset("labelsure_prototype", "1")
    snap = mock_snapshot()
    mrp_rule = next(r for r in ruleset.rules if r.rule_key == "MRP_PRESENCE")
    qty_rule = next(r for r in ruleset.rules if r.rule_key == "NET_QUANTITY_STRUCTURE")
    mfg_rule = next(r for r in ruleset.rules if r.rule_key == "MONTH_YEAR_STRUCTURE")
    care_rule = next(r for r in ruleset.rules if r.rule_key == "CONSUMER_CONTACT_DEMO")

    assert evaluate_rule(mrp_rule, snap)["verdict"] == "PASS"
    assert evaluate_rule(qty_rule, snap)["verdict"] == "PASS"
    assert evaluate_rule(mfg_rule, snap)["verdict"] == "PASS"
    assert evaluate_rule(care_rule, snap)["verdict"] == "PASS"

def test_overall_aggregation():
    assert aggregate([{"verdict": "PASS"}, {"verdict": "PASS"}]) == "PASS"
    assert aggregate([{"verdict": "PASS"}, {"verdict": "NOT_APPLICABLE"}]) == "PASS"
    assert aggregate([{"verdict": "PASS"}, {"verdict": "UNCERTAIN"}]) == "UNCERTAIN"
    assert aggregate([{"verdict": "PASS"}, {"verdict": "FAIL"}]) == "FAIL"
    assert aggregate([{"verdict": "UNCERTAIN"}, {"verdict": "FAIL"}]) == "FAIL"

def test_rule_evaluation_api_full_flow(client):
    base, user_h, _ = prepare(client, SYNTHETIC)
    admin_h = auth_headers(client, "admin@labelsure.local")
    sup_h = auth_headers(client, "supervisor@labelsure.local")

    # Run extraction and context resolution
    client.post(base + "/extract-declarations", headers=user_h).raise_for_status()
    client.post(base + "/resolve-context", json={"inspector_input": {"import_status": "DOMESTIC", "package_type": "POUCH", "product_category": "FOOD"}}, headers=user_h).raise_for_status()
    snapshot = client.get(base + "/rule-input", headers=user_h).json()
    snapshot_id = snapshot["id"]

    # Evaluate (with allow_prototype_rules)
    eval_res = client.post(base + "/evaluate", headers=user_h, json={"allow_prototype_rules": True})
    assert eval_res.status_code == 200
    summary = eval_res.json()
    assert summary["status"] == "SUCCESS"
    assert summary["total_rules"] >= 4
    assert summary["prototype"] is True
    assert summary["rule_input_snapshot_id"] == snapshot_id

    # Get summary
    sum_res = client.get(base + "/evaluation", headers=user_h)
    assert sum_res.status_code == 200
    assert sum_res.json()["is_current"] is True

    # Get results list
    res_list = client.get(base + "/evaluation/results", headers=user_h)
    assert res_list.status_code == 200
    results = res_list.json()
    assert len(results) >= 4
    assert all("evidence" in r for r in results)

    # Get single result detail
    first_id = results[0]["id"]
    det_res = client.get(base + f"/evaluation/results/{first_id}", headers=user_h)
    assert det_res.status_code == 200
    assert det_res.json()["id"] == first_id

    # RBAC: Supervisor read-only
    sup_sum = client.get(base + "/evaluation", headers=sup_h)
    assert sup_sum.status_code == 200
    # Supervisor cannot run evaluation
    sup_eval = client.post(base + "/evaluate", headers=sup_h, json={"allow_prototype_rules": True})
    assert sup_eval.status_code == 403

    # RBAC: Admin full access
    admin_sum = client.get(base + "/evaluation", headers=admin_h)
    assert admin_sum.status_code == 200

    # Idempotent evaluation returns existing summary
    eval_again = client.post(base + "/evaluate", headers=user_h, json={"allow_prototype_rules": True})
    assert eval_again.status_code == 200
    assert eval_again.json()["id"] == summary["id"]
