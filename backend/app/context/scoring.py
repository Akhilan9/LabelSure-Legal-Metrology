SOURCE_PRIORITY = {"MANUAL_OVERRIDE":60,"INSPECTOR_INPUT":50,"INSPECTION_METADATA":40,
                   "DECLARATION_CANDIDATE":30,"OCR_EVIDENCE":20,"SYSTEM_INFERENCE":10}

def evidence_confidence(candidate):
    # Preserve native extraction confidence instead of manufacturing a new probability.
    value = candidate.get("confidence_score")
    return max(0.0,min(1.0,float(value))) if value is not None else None

def candidate_state(candidate):
    confidence = evidence_confidence(candidate)
    return "REVIEW_REQUIRED" if candidate.get("needs_review") or confidence is None or confidence < .80 else "INFERRED"

