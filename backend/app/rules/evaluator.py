from decimal import Decimal, InvalidOperation
from app.rules.conditions import condition, referenced_keys

def parsed(candidate,validator):
    data=candidate.get("structured_value",{})
    if validator=="presence": return bool(candidate.get("normalized_value","").strip())
    if validator=="net_quantity":
        try:
            number=Decimal(str(data.get("numeric_value")))
            return number.is_finite() and number>0 and data.get("unit") in {"g","kg","ml","L","count","m","cm","mm","m2","m²"}
        except (InvalidOperation,ValueError): return False
    if validator=="month_year":
        return type(data.get("year")) is int and 1<=data["year"]<=9999 and type(data.get("month")) is int and 1<=data["month"]<=12
    return False

def evaluate_rule(rule, snapshot):
    applicable = condition(rule.applicability_conditions, snapshot["context_keys"])
    candidates = [c for c in snapshot["declarations"] if c["declaration_type"] in rule.required_declaration_types]
    facts = {fact_id for key in referenced_keys(rule.applicability_conditions)
           for fact_id in snapshot["context_keys"].get(key,{}).get("fact_ids",[])}
    base = {
        "rule_id": rule.rule_id, "rule_key": rule.rule_key, "rule_version": rule.rule_version,
        "title": rule.title, "legal_reference": rule.legal_reference, "legal_status": rule.legal_status,
        "severity": rule.severity, "rule_definition": rule.model_dump(mode="json"),
        "applicability_state": "APPLICABLE" if applicable is True else "NOT_APPLICABLE" if applicable is False else "UNKNOWN",
        "candidate_ids": [c["id"] for c in candidates], "context_fact_ids": sorted(facts),
        "evidence_confidence": min((c["confidence_score"] for c in candidates), default=None)
    }

    def result(verdict, reason, explanation):
        return {**base, "verdict": verdict, "reason_code": reason, "explanation": explanation}

    # Check if OCR processing failed for evidence
    ocr_inputs = snapshot.get("source_inputs", {}).get("ocr", [])
    if any(o.get("status") == "FAILED" for o in ocr_inputs):
        return result("UNCERTAIN", "OCR_FAILED", "OCR evidence failed to extract text cleanly; human review required.")

    if applicable is False:
        return result("NOT_APPLICABLE", "RULE_NOT_APPLICABLE", f"Statutory provision ({rule.legal_reference}) is not applicable to this product type or packaging configuration.")

    if applicable is None:
        if rule.applicability_conditions == {"key": "package.type", "operator": "exists"}:
            applicable = True
        else:
            return result("UNCERTAIN", "CONTEXT_UNKNOWN", f"Statutory rule applicability for {rule.title} cannot be evaluated because package context is unknown.")

    # Core statutory mandatory declarations required under Rule 6(1) of LMPC Rules, 2011
    MANDATORY_KEYS = {
        "COMMON_NAME", "COMMON_PRODUCT_NAME",
        "NET_QUANTITY",
        "MRP",
        "MANUFACTURER", "MANUFACTURER_NAME", "MANUFACTURER_ADDRESS",
        "CONSUMER_CARE", "CONSUMER_CARE_PHONE", "CONSUMER_CARE_EMAIL",
        "PACKING_DATE"
    }

    if candidates:
        # Check for conflicting candidates
        distinct_vals = {c.get("normalized_value", "").strip().lower() for c in candidates if c.get("normalized_value")}
        if len(distinct_vals) > 1 and rule.rule_key not in {"COMMON_NAME", "COMMON_PRODUCT_NAME", "CONSUMER_CARE", "CONSUMER_CARE_PHONE", "CONSUMER_CARE_EMAIL"}:
            return result("UNCERTAIN", "CONFLICTING_CANDIDATES", f"Multiple conflicting declaration candidates detected for {rule.title}.")

        # Check Expiry / Best Before Date specifically for expired product rejection
        if rule.rule_key in {"EXPIRY", "EXPIRY_DATE", "BEST_BEFORE"}:
            from datetime import datetime
            import re
            now = datetime.now()
            for c in candidates:
                val = c.get("normalized_value", "").strip()
                exp_date = None
                m_iso = re.match(r"^(\d{4})[/-](\d{1,2})(?:[/-](\d{1,2}))?", val)
                m_dmy = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", val)
                m_my = re.match(r"^(\d{1,2})[/-](\d{2,4})$", val)
                if m_iso:
                    y, m = int(m_iso.group(1)), int(m_iso.group(2))
                    exp_date = (y, m)
                elif m_dmy:
                    d, m, y_str = int(m_dmy.group(1)), int(m_dmy.group(2)), m_dmy.group(3)
                    y = int(y_str) if len(y_str) == 4 else (2000 + int(y_str))
                    if d > 12 and 1 <= m <= 12:
                        exp_date = (y, m)
                    elif m > 12 and 1 <= d <= 12:
                        exp_date = (y, d)
                    elif 1 <= m <= 12:
                        exp_date = (y, m)
                elif m_my:
                    m, y_str = int(m_my.group(1)), m_my.group(2)
                    y = int(y_str) if len(y_str) == 4 else (2000 + int(y_str))
                    if 1 <= m <= 12:
                        exp_date = (y, m)
                if exp_date and exp_date < (now.year, now.month):
                    return result(
                        "FAIL",
                        "EXPIRED_COMMODITY_REJECTED",
                        f"REJECTED - EXPIRED PRODUCT: Declared Expiry/Best Before date '{val}' is past current date. Sale or distribution of expired commodity is illegal under LMPC Rule 6(1)(da) & Section 36 of Legal Metrology Act, 2009."
                    )

        # Check if candidate value satisfies parsed validator
        valid_candidates = [c for c in candidates if parsed(c, rule.evaluation_conditions.validator)]
        if valid_candidates:
            val_str = ", ".join(f"'{c['normalized_value']}'" for c in valid_candidates)
            return result(
                "PASS",
                "DECLARATION_PRESENT",
                f"Statutory declaration for {rule.title} ({val_str}) is present and verified on package label under {rule.legal_reference}."
            )
        else:
            # Candidate exists but failed structural validation
            raw_str = ", ".join(f"'{c.get('raw_value') or c.get('normalized_value')}'" for c in candidates)
            return result(
                "FAIL",
                "INVALID_DECLARATION_FORMAT",
                f"REJECTED - FORMAT VIOLATION: Statutory declaration for {rule.title} ('{raw_str}') was detected but violates statutory formatting requirements under {rule.legal_reference}."
            )
    else:
        # Candidate not detected in OCR extractions
        is_mandatory = rule.rule_key in MANDATORY_KEYS or any(k in MANDATORY_KEYS for k in rule.required_declaration_types)
        if is_mandatory:
            return result(
                "FAIL",
                "DECLARATION_NOT_DETECTED",
                f"REJECTED - MISSING MANDATORY DECLARATION: Statutory declaration for {rule.title} was NOT detected on package packaging. Violates {rule.legal_reference} & Section 36 of Legal Metrology Act, 2009."
            )
        else:
            return result(
                "NOT_APPLICABLE",
                "CONDITIONAL_RULE_EXEMPT",
                f"Declaration for {rule.title} is conditional and not required for this product category under {rule.legal_reference}."
            )

def aggregate(results):
    if any(r["verdict"] == "FAIL" for r in results):
        return "FAIL"
    if any(r["verdict"] == "UNCERTAIN" for r in results):
        return "UNCERTAIN"
    if any(r["verdict"] == "PASS" for r in results):
        return "PASS"
    return "NOT_APPLICABLE"



