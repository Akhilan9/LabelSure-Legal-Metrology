import pytest
from app.rules.evaluator import evaluate_rule, aggregate
from app.rules.schemas import RuleDefinition
from app.models.extraction import DeclarationType

def make_rule(rule_key, title, legal_ref, decl_type, validator="presence", mandatory=True):
    return RuleDefinition.model_validate({
        "rule_id": f"TEST-{rule_key}",
        "rule_version": "1",
        "rule_key": rule_key,
        "title": title,
        "description": f"Statutory requirement for {title}",
        "legal_reference": legal_ref,
        "legal_status": "PROTOTYPE_RULE",
        "effective_from": None,
        "effective_to": None,
        "applicability_conditions": {"key": "package.type", "operator": "exists"},
        "evaluation_conditions": {"validator": validator, "composition": "all"},
        "required_declaration_types": [decl_type],
        "severity": "HIGH",
        "evidence_requirements": {
            "min_confidence": 0.50,
            "allow_absence_failure": mandatory,
            "required_panels": ["DECLARATION_PANEL"],
            "accepted_quality": ["GOOD", "ACCEPTABLE"]
        },
        "uncertainty_behavior": "UNCERTAIN",
        "enabled": True,
        "verification_metadata": {
            "source": "https://consumeraffairs.gov.in/pages/legal-metrology-act",
            "source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "reviewer": "Inspector Admin",
            "verified_at": "2026-09-08T00:00:00Z"
        }
    })

def make_snapshot(declarations):
    return {
        "context_keys": {"package.type": {"fact_ids": ["f1"]}},
        "declarations": declarations,
        "source_inputs": {
            "extraction_run_id": "ext-1",
            "extraction_status": "SUCCESS",
            "images": [{"id": "img-1", "quality": "GOOD", "panel": "DECLARATION_PANEL"}],
            "ocr": [{"image_id": "img-1", "status": "SUCCESS", "block_count": 10, "confidence": 0.95}]
        },
        "evidence": {"state": "SUFFICIENT"}
    }


def test_pass_fully_compliant_packaged_commodity():
    """
    Test Case 1: FULLY COMPLIANT PACKAGED COMMODITY
    Statutory Reference: Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)
    Verifies that a product with valid MRP, Net Quantity, Mfg Date, Future Expiry Date, 
    Manufacturer details, Consumer Care helpline, and Generic Name passes evaluation.
    """
    snapshot = make_snapshot([
        {"id": "d1", "declaration_type": DeclarationType.COMMON_PRODUCT_NAME.value, "normalized_value": "Amul Butter", "confidence_score": 0.95, "structured_value": {}},
        {"id": "d2", "declaration_type": DeclarationType.NET_QUANTITY.value, "normalized_value": "500 g", "confidence_score": 0.95, "structured_value": {"numeric_value": "500", "unit": "g"}},
        {"id": "d3", "declaration_type": DeclarationType.MRP.value, "normalized_value": "275.00", "confidence_score": 0.95, "structured_value": {}},
        {"id": "d4", "declaration_type": DeclarationType.MONTH_YEAR.value, "normalized_value": "2026-08", "confidence_score": 0.95, "structured_value": {"year": 2026, "month": 8}},
        {"id": "d5", "declaration_type": DeclarationType.EXPIRY_DATE.value, "normalized_value": "2026-12", "confidence_score": 0.95, "structured_value": {"year": 2026, "month": 12}},
        {"id": "d6", "declaration_type": DeclarationType.MANUFACTURER_NAME.value, "normalized_value": "GCMMF Ltd, Anand 388001", "confidence_score": 0.95, "structured_value": {}},
        {"id": "d7", "declaration_type": DeclarationType.CONSUMER_CARE_PHONE.value, "normalized_value": "18002583333", "confidence_score": 0.95, "structured_value": {}}
    ])

    rules = [
        make_rule("COMMON_NAME", "Common commodity name", "LMPC Rules, 2011: Rule 6(1)(b)", DeclarationType.COMMON_PRODUCT_NAME.value),
        make_rule("NET_QUANTITY", "Net quantity", "LMPC Rules, 2011: Rule 6(1)(c)", DeclarationType.NET_QUANTITY.value, validator="net_quantity"),
        make_rule("MRP", "Retail price declaration", "LMPC Rules, 2011: Rule 6(1)(e)", DeclarationType.MRP.value),
        make_rule("PACKING_DATE", "Month & Year of Packaging", "LMPC Rules, 2011: Rule 6(1)(d)", DeclarationType.MONTH_YEAR.value, validator="month_year"),
        make_rule("EXPIRY", "Best Before / Expiry Date", "LMPC Rules, 2011: Rule 6(1)(da)", DeclarationType.EXPIRY_DATE.value, validator="month_year"),
        make_rule("MANUFACTURER", "Manufacturer Name & Address", "LMPC Rules, 2011: Rule 6(1)(a)", DeclarationType.MANUFACTURER_NAME.value),
        make_rule("CONSUMER_CARE", "Consumer Care Helpline", "LMPC Rules, 2011: Rule 6(1)(h)", DeclarationType.CONSUMER_CARE_PHONE.value)
    ]

    results = [evaluate_rule(r, snapshot) for r in rules]
    assert all(r["verdict"] == "PASS" for r in results)
    assert aggregate(results) == "PASS"


def test_fail_expired_commodity_rejection():
    """
    Test Case 2: REJECTED EXPIRED PRODUCT
    Statutory Reference: Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(da) & Section 36 of Legal Metrology Act, 2009.
    Verifies that a product with an Expiry Date in the past (e.g. 2024-01) is immediately rejected with EXPIRED_COMMODITY_REJECTED.
    """
    snapshot = make_snapshot([
        {"id": "d1", "declaration_type": DeclarationType.COMMON_PRODUCT_NAME.value, "normalized_value": "Pasteurized Milk", "confidence_score": 0.95, "structured_value": {}},
        {"id": "d2", "declaration_type": DeclarationType.NET_QUANTITY.value, "normalized_value": "500 ml", "confidence_score": 0.95, "structured_value": {"numeric_value": "500", "unit": "ml"}},
        {"id": "d3", "declaration_type": DeclarationType.MRP.value, "normalized_value": "34.00", "confidence_score": 0.95, "structured_value": {}},
        {"id": "d4", "declaration_type": DeclarationType.EXPIRY_DATE.value, "normalized_value": "2024-01", "confidence_score": 0.95, "structured_value": {"year": 2024, "month": 1}}
    ])

    rule = make_rule("EXPIRY", "Best Before / Expiry Date", "LMPC Rules, 2011: Rule 6(1)(da)", DeclarationType.EXPIRY_DATE.value, validator="month_year")
    res = evaluate_rule(rule, snapshot)

    assert res["verdict"] == "FAIL"
    assert res["reason_code"] == "EXPIRED_COMMODITY_REJECTED"
    assert "REJECTED - EXPIRED PRODUCT" in res["explanation"]
    assert aggregate([res]) == "FAIL"


def test_fail_missing_mandatory_mrp_and_net_quantity():
    """
    Test Case 3: REJECTED MISSING MANDATORY DECLARATIONS
    Statutory Reference: Legal Metrology Act, 2009 - Section 36 & LMPC Rules, 2011 Rule 6(1)(c), Rule 6(1)(e).
    Verifies that missing mandatory MRP and Net Quantity declarations trigger direct statutory rejection (FAIL).
    """
    snapshot = make_snapshot([
        {"id": "d1", "declaration_type": DeclarationType.COMMON_PRODUCT_NAME.value, "normalized_value": "Wheat Flour", "confidence_score": 0.95, "structured_value": {}}
    ])

    rule_mrp = make_rule("MRP", "Retail price declaration", "LMPC Rules, 2011: Rule 6(1)(e)", DeclarationType.MRP.value)
    rule_qty = make_rule("NET_QUANTITY", "Net quantity", "LMPC Rules, 2011: Rule 6(1)(c)", DeclarationType.NET_QUANTITY.value, validator="net_quantity")

    res_mrp = evaluate_rule(rule_mrp, snapshot)
    res_qty = evaluate_rule(rule_qty, snapshot)

    assert res_mrp["verdict"] == "FAIL"
    assert res_mrp["reason_code"] == "DECLARATION_NOT_DETECTED"
    assert "REJECTED - MISSING MANDATORY DECLARATION" in res_mrp["explanation"]

    assert res_qty["verdict"] == "FAIL"
    assert res_qty["reason_code"] == "DECLARATION_NOT_DETECTED"
    assert aggregate([res_mrp, res_qty]) == "FAIL"


def test_fail_invalid_metric_unit_format_violation():
    """
    Test Case 4: REJECTED NON-STANDARD METRIC UNIT FORMAT
    Statutory Reference: Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 13 & Rule 6(1)(c).
    Verifies that declaring quantity in non-standard units (e.g., '500 lbs') triggers format violation rejection (FAIL).
    """
    snapshot = make_snapshot([
        {"id": "d1", "declaration_type": DeclarationType.NET_QUANTITY.value, "normalized_value": "500 lbs", "confidence_score": 0.90, "structured_value": {"numeric_value": "500", "unit": "lbs"}}
    ])

    rule = make_rule("NET_QUANTITY", "Net quantity", "LMPC Rules, 2011: Rule 6(1)(c)", DeclarationType.NET_QUANTITY.value, validator="net_quantity")
    res = evaluate_rule(rule, snapshot)

    assert res["verdict"] == "FAIL"
    assert res["reason_code"] == "INVALID_DECLARATION_FORMAT"
    assert "REJECTED - FORMAT VIOLATION" in res["explanation"]
    assert aggregate([res]) == "FAIL"
