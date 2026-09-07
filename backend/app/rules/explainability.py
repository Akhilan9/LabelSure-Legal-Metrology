"""RuleLens Explainability and Evidence Traceability Engine.
Generates comprehensive, deterministic, human-auditable explanations for Legal Metrology rule verdicts.
"""
from typing import Any
from app.rules.schemas import RuleDefinition


def explain_result(result: dict, run_data: dict, snapshot_content: dict) -> dict:
    """
    Build a rich, structured explainability payload linking a rule evaluation result
    to its exact evidence provenance, AST condition evaluations, and decision trace.
    """
    rule_def = result.get("rule_definition") or {}
    verdict = result.get("verdict")
    reason_code = result.get("reason_code")
    explanation_text = result.get("explanation")
    rule_key = result.get("rule_key")
    rule_id = result.get("rule_id")
    legal_reference = result.get("legal_reference")
    severity = result.get("severity")
    legal_status = result.get("legal_status")

    # Extract snapshot components
    context_keys = snapshot_content.get("context_keys", {})
    facts = snapshot_content.get("facts", [])
    declarations = snapshot_content.get("declarations", [])
    images = snapshot_content.get("source_inputs", {}).get("images", [])
    ocr_runs = snapshot_content.get("source_inputs", {}).get("ocr", [])

    # 1. Trace Applicability
    app_cond = rule_def.get("applicability_conditions", {})
    applicability_trace = _trace_applicability(app_cond, context_keys, facts)

    # 2. Trace Evidence Sufficiency
    sufficiency_trace = _trace_sufficiency(snapshot_content, rule_def)

    # 3. Trace Declaration Candidates & OCR
    candidate_trace = _trace_candidates(rule_def, declarations)

    # 4. Build Decision Trace Steps
    decision_trace = _build_decision_trace(
        verdict=verdict,
        reason_code=reason_code,
        rule_def=rule_def,
        applicability_trace=applicability_trace,
        sufficiency_trace=sufficiency_trace,
        candidate_trace=candidate_trace,
        context_keys=context_keys
    )

    # 5. Build Counterfactual Guidance
    counterfactual = _build_counterfactual(verdict, reason_code, rule_def, candidate_trace)

    # 6. Gather Linked Evidence Artifacts
    evidence_items = result.get("evidence", [])
    linked_evidence = _gather_linked_evidence(
        evidence_items=evidence_items,
        declarations=declarations,
        facts=facts,
        images=images,
        ocr_runs=ocr_runs
    )

    return {
        "rule_id": rule_id,
        "rule_key": rule_key,
        "rule_version": result.get("rule_version"),
        "title": result.get("title"),
        "legal_reference": legal_reference,
        "legal_status": legal_status,
        "severity": severity,
        "verdict": verdict,
        "reason_code": reason_code,
        "explanation": explanation_text,
        "applicability_state": result.get("applicability_state"),
        "evidence_confidence": result.get("evidence_confidence"),
        "applicability_trace": applicability_trace,
        "sufficiency_trace": sufficiency_trace,
        "candidate_trace": candidate_trace,
        "decision_trace": decision_trace,
        "counterfactual_guidance": counterfactual,
        "linked_evidence": linked_evidence,
        "legal_disclaimer": (
            "PROTOTYPE RULE: For research & automated trial evaluation only. Requires manual inspector verification under Legal Metrology Act, 2009."
            if legal_status == "PROTOTYPE_RULE" else
            "VERIFIED STATUTORY RULE: Enforced pursuant to Legal Metrology (Packaged Commodities) Rules, 2011."
        )
    }


def _trace_applicability(cond_node: dict, context_keys: dict, facts: list) -> dict:
    if not cond_node:
        return {
            "is_applicable": True,
            "condition_tree": None,
            "evaluated_keys": [],
            "summary": "Rule applies universally to all packaged commodities."
        }

    evaluated_keys = []

    def walk(node):
        if "key" in node:
            k = node["key"]
            item = context_keys.get(k, {})
            matching_facts = [f for f in facts if f.get("fact_type") == k.split(".")[-1].upper()]
            evaluated_keys.append({
                "key": k,
                "expected_operator": node.get("operator"),
                "expected_value": node.get("value"),
                "current_state": item.get("state", "UNKNOWN"),
                "current_value": item.get("value"),
                "fact_references": item.get("fact_ids", []),
                "supporting_facts": matching_facts
            })
        for child in node.get("all", []) + node.get("any", []) + node.get("none", []):
            walk(child)

    walk(cond_node)

    return {
        "is_applicable": True,
        "condition_tree": cond_node,
        "evaluated_keys": evaluated_keys,
        "summary": "Applicability conditions evaluated against resolved inspection context."
    }


def _trace_sufficiency(snapshot_content: dict, rule_def: dict) -> dict:
    source_inputs = snapshot_content.get("source_inputs", {})
    images = source_inputs.get("images", [])
    ocr_list = source_inputs.get("ocr", [])

    total_images = len(images)
    good_quality_images = sum(1 for img in images if img.get("quality") in {"GOOD", "ACCEPTABLE"})
    successful_ocr = sum(1 for o in ocr_list if o.get("status") == "SUCCESS")

    reqs = rule_def.get("evidence_requirements", {})

    return {
        "total_images": total_images,
        "good_quality_images": good_quality_images,
        "successful_ocr_runs": successful_ocr,
        "allows_absence_fail": reqs.get("allow_absence_fail", False),
        "required_panel_types": reqs.get("required_panel_types", []),
        "min_ocr_confidence": reqs.get("min_ocr_confidence", 0.60),
        "is_evidence_sufficient": good_quality_images > 0 and successful_ocr > 0
    }


def _trace_candidates(rule_def: dict, declarations: list) -> list:
    req_types = set(rule_def.get("required_declaration_types", []))
    matching = [d for d in declarations if d.get("declaration_type") in req_types]

    return [
        {
            "id": d.get("id"),
            "declaration_type": d.get("declaration_type"),
            "raw_value": d.get("raw_value"),
            "normalized_value": d.get("normalized_value"),
            "confidence_score": d.get("confidence_score"),
            "source_image_id": d.get("source_image_id"),
            "needs_review": d.get("needs_review", False),
            "review_reasons": d.get("review_reasons", []),
            "structured_value": d.get("structured_value", {}),
            "sources": d.get("sources", [])
        }
        for d in matching
    ]


def _build_decision_trace(
    verdict: str,
    reason_code: str,
    rule_def: dict,
    applicability_trace: dict,
    sufficiency_trace: dict,
    candidate_trace: list,
    context_keys: dict
) -> list:
    steps = []

    # Step 1: Context & Applicability Check
    if verdict == "NOT_APPLICABLE":
        steps.append({
            "step_number": 1,
            "phase": "APPLICABILITY_EVALUATION",
            "status": "NOT_APPLICABLE",
            "title": "Rule Inapplicable Under Current Package Context",
            "detail": f"Applicability conditions did not match package context. Reason: {reason_code}."
        })
        return steps
    elif verdict == "UNCERTAIN" and reason_code == "CONTEXT_UNKNOWN":
        steps.append({
            "step_number": 1,
            "phase": "APPLICABILITY_EVALUATION",
            "status": "UNCERTAIN",
            "title": "Ambiguous Package Context",
            "detail": "Applicability could not be conclusively determined because required context keys are UNKNOWN."
        })
        return steps
    else:
        steps.append({
            "step_number": 1,
            "phase": "APPLICABILITY_EVALUATION",
            "status": "PASSED",
            "title": "Rule Applicability Confirmed",
            "detail": "Inspection context satisfies all statutory applicability preconditions."
        })

    # Step 2: Technical Evidence Sufficiency
    if verdict == "UNCERTAIN" and reason_code in {"OCR_FAILED", "INSUFFICIENT_EVIDENCE", "IMAGE_QUALITY_INADEQUATE"}:
        steps.append({
            "step_number": 2,
            "phase": "EVIDENCE_SUFFICIENCY",
            "status": "FAILED",
            "title": "Technical Evidence Threshold Not Met",
            "detail": f"OCR or photographic evidence quality is inadequate to evaluate compliance. Reason: {reason_code}."
        })
        return steps
    else:
        steps.append({
            "step_number": 2,
            "phase": "EVIDENCE_SUFFICIENCY",
            "status": "PASSED",
            "title": "Evidence Sufficiency Verified",
            "detail": f"Photographic quality and OCR extraction meet confidence thresholds (≥ {sufficiency_trace.get('min_ocr_confidence', 0.60):.2f})."
        })

    # Step 3: Candidate Extraction & Consistency
    if len(candidate_trace) == 0:
        if verdict == "FAIL" and reason_code == "DECLARATION_NOT_DETECTED":
            steps.append({
                "step_number": 3,
                "phase": "DECLARATION_DETECTION",
                "status": "VIOLATION",
                "title": "Mandatory Statutory Declaration Missing",
                "detail": "No candidate declaration matching statutory requirements was found on clear, readable package panels."
            })
        else:
            steps.append({
                "step_number": 3,
                "phase": "DECLARATION_DETECTION",
                "status": "UNCERTAIN",
                "title": "Declaration Candidate Undetected",
                "detail": "Candidate was not detected, but absence cannot be legally confirmed as a violation without human inspection."
            })
    elif len(candidate_trace) > 1 and reason_code == "CONFLICTING_CANDIDATES":
        steps.append({
            "step_number": 3,
            "phase": "DECLARATION_DETECTION",
            "status": "CONFLICT",
            "title": "Conflicting Multiple Declarations Detected",
            "detail": f"Found {len(candidate_trace)} competing candidates with differing normalized values. Inspector disambiguation required."
        })
    else:
        steps.append({
            "step_number": 3,
            "phase": "DECLARATION_DETECTION",
            "status": "PASSED",
            "title": f"Declaration Candidate Extracted ({candidate_trace[0].get('normalized_value')})",
            "detail": f"Extracted candidate '{candidate_trace[0].get('normalized_value')}' with confidence {candidate_trace[0].get('confidence_score', 0):.2f}."
        })

    # Step 4: Rule Logic & Legal Evaluation
    if verdict == "PASS":
        steps.append({
            "step_number": 4,
            "phase": "STATUTORY_VERIFICATION",
            "status": "COMPLIANT",
            "title": "Statutory Structure & Legal Format Verified",
            "detail": f"Declaration satisfies all statutory rules per {rule_def.get('legal_reference')}."
        })
    elif verdict == "FAIL":
        steps.append({
            "step_number": 4,
            "phase": "STATUTORY_VERIFICATION",
            "status": "NON_COMPLIANT",
            "title": "Statutory Non-Compliance Identified",
            "detail": f"Declaration violates legal metrology standards. Code: {reason_code}."
        })
    elif verdict == "UNCERTAIN":
        steps.append({
            "step_number": 4,
            "phase": "STATUTORY_VERIFICATION",
            "status": "NEEDS_HUMAN_REVIEW",
            "title": "Uncertainty / Human Review Required",
            "detail": f"Automated rules cannot conclude definitively ({reason_code}). Inspector intervention mandatory."
        })

    return steps


def _build_counterfactual(verdict: str, reason_code: str, rule_def: dict, candidate_trace: list) -> str:
    if verdict == "PASS":
        return "Statutory requirement is satisfied. No corrective action required."
    elif verdict == "NOT_APPLICABLE":
        return "If package classification changes (e.g. from DOMESTIC to IMPORTED), this statutory rule will become applicable and require verification."
    elif verdict == "UNCERTAIN":
        if reason_code == "OCR_FAILED":
            return "Re-capture clear, well-lit photo of the declaration panel and re-run OCR extraction to allow automated evaluation."
        elif reason_code == "CONFLICTING_CANDIDATES":
            return "An inspector must select the authentic declaration candidate and reject erroneous/misrecognized OCR candidates in the review workspace."
        elif reason_code == "CONTEXT_UNKNOWN":
            return "Specify missing product/package context attributes (e.g., package type, import status) in the Context & Applicability section."
        else:
            return "An authorized inspector must manually verify the physical label and record a formal review decision."
    elif verdict == "FAIL":
        if reason_code == "DECLARATION_NOT_DETECTED":
            return "Ensure the mandatory declaration is printed prominently on the principal display panel or declaration panel as mandated by Legal Metrology (Packaged Commodities) Rules, 2011."
        elif reason_code == "NET_QUANTITY_INVALID_UNIT":
            return "Use standard SI units (g, kg, ml, L, count) in accordance with Second Schedule of Legal Metrology (Packaged Commodities) Rules, 2011."
        else:
            return f"Rectify packaging label to conform with {rule_def.get('legal_reference', 'statutory requirements')}."
    return "Review label evidence against Legal Metrology guidelines."


def _gather_linked_evidence(
    evidence_items: list,
    declarations: list,
    facts: list,
    images: list,
    ocr_runs: list
) -> dict:
    linked_declarations = []
    linked_facts = []
    linked_images = []
    linked_ocr_blocks = []

    decl_map = {d.get("id"): d for d in declarations}
    fact_map = {f.get("id"): f for f in facts}
    img_map = {img.get("id"): img for img in images}

    for ev in evidence_items:
        c_id = ev.get("declaration_candidate_id")
        if c_id and c_id in decl_map:
            linked_declarations.append(decl_map[c_id])

        f_id = ev.get("context_fact_id")
        if f_id and f_id in fact_map:
            linked_facts.append(fact_map[f_id])

        img_id = ev.get("inspection_image_id")
        if img_id and img_id in img_map:
            linked_images.append(img_map[img_id])

    return {
        "declarations": linked_declarations,
        "facts": linked_facts,
        "images": linked_images,
        "raw_evidence_links": evidence_items
    }
