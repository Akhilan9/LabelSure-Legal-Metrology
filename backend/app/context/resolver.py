from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5
from app.context.facts import FIELDS, PRESENCE, KEYS, normalize, quantity_kind, matching, safe
from app.context.scoring import SOURCE_PRIORITY, candidate_state, evidence_confidence
from app.context.applicability import preview

def resolve(bundle, fingerprint):
    facts = []
    def add(kind,value,source,reference=None,confidence=None,state="KNOWN",explanation="",raw=None,refs=None):
        facts.append({"id":str(uuid5(NAMESPACE_URL,fingerprint+":"+str(len(facts)))),
            "fact_type":kind,"value":{"normalized":value,"raw":safe(raw) if raw is not None else value,"references":refs or []},
            "source_type":source,"source_reference_id":reference,"confidence":confidence,
            "resolution_state":state,"explanation":explanation,"is_active":True})
    metadata = bundle["metadata"]
    for field,kind in FIELDS.items():
        raw = metadata.get(field)
        if raw is not None:
            value = normalize(kind,raw)
            add(kind,value,"INSPECTION_METADATA",bundle["inspection_id"],state="UNKNOWN" if value=="UNKNOWN" else "KNOWN",
                raw=raw,explanation="Inspector-entered inspection metadata; no machine confidence assigned.")
        if field in bundle["inspector_input"] and bundle["inspector_input"][field] is not None:
            raw = bundle["inspector_input"][field]
            value = normalize(kind,raw)
            add(kind,value,"INSPECTOR_INPUT",bundle["inspection_id"],state="UNKNOWN" if value=="UNKNOWN" else "KNOWN",
                raw=raw,explanation="Explicit inspector context input; retained separately from inspection metadata.")
    candidates = bundle["candidates"]
    for candidate in candidates:
        kind = candidate["declaration_type"]
        if kind not in {"COUNTRY_OF_ORIGIN","NET_QUANTITY","IMPORTER_NAME","IMPORTER_ADDRESS"}:
            continue
        target = "COUNTRY_OF_ORIGIN" if kind=="COUNTRY_OF_ORIGIN" else "QUANTITY_KIND" if kind=="NET_QUANTITY" else "IMPORT_STATUS"
        value = candidate["normalized_value"] if target=="COUNTRY_OF_ORIGIN" else quantity_kind(candidate["structured_value"].get("unit")) if target=="QUANTITY_KIND" else "IMPORTED"
        state = candidate_state(candidate)
        explanation = "Extraction confidence preserved; inspect linked OCR evidence."
        if target=="IMPORT_STATUS":
            # An importer candidate is a possible signal, never a confirmed imported classification.
            state = "REVIEW_REQUIRED"
            explanation = "Importer candidate suggests possible imported context; does not confirm import status."
        if value=="UNKNOWN":
            state="UNKNOWN"
        add(target,value,"DECLARATION_CANDIDATE",candidate["id"],evidence_confidence(candidate),state,
            explanation,raw=candidate["raw_value"],refs=[s["ocr_block_id"] for s in candidate["sources"]])
    for prefix,(kind,key) in PRESENCE.items():
        found = matching(candidates,prefix)
        detected = bool(found) if bundle["extraction_run_id"] else None
        add(kind,detected,"SYSTEM_INFERENCE",bundle["extraction_run_id"],
            state="KNOWN" if detected is not None else "UNKNOWN",
            explanation="Candidate detection only. False means no candidate detected, never legal absence.",
            refs=[c["id"] for c in found])
    ocr = bundle["ocr"]
    usable = [r for r in ocr if r["status"] in {"SUCCESS","PARTIAL"} and r["block_count"]>0]
    confidence_values = [r["confidence"] for r in usable if r["confidence"] is not None]
    ocr_state = "UNKNOWN" if len(confidence_values)!=len(usable) or not confidence_values else "LOW" if min(confidence_values)<.60 else "REVIEW" if min(confidence_values)<.85 else "GOOD"
    add("OCR_EVIDENCE_AVAILABLE",bool(usable),"OCR_EVIDENCE",state="KNOWN",
        explanation="At least one latest OCR run contains usable text.",refs=[r["id"] for r in usable])
    add("OCR_CONFIDENCE_STATE",ocr_state,"OCR_EVIDENCE",state="UNKNOWN" if ocr_state=="UNKNOWN" else "KNOWN",
        explanation="Minimum latest usable run confidence; GOOD >=0.85, REVIEW >=0.60, otherwise LOW.",
        refs=[r["id"] for r in usable])
    declaration_conflicts = [c["id"] for c in candidates if "Conflicting candidates" in c["review_reasons"]]
    add("DECLARATION_CONFLICT_PRESENT",bool(declaration_conflicts) if bundle["extraction_run_id"] else None,
        "SYSTEM_INFERENCE",bundle["extraction_run_id"],state="KNOWN" if bundle["extraction_run_id"] else "UNKNOWN",
        explanation="Conflicts flagged during declaration extraction.",refs=declaration_conflicts)
    grouped = defaultdict(list)
    for fact in facts:
        grouped[fact["fact_type"]].append(fact)
    resolved,conflicts = {},[]
    for kind in FIELDS.values():
        sources = grouped[kind]
        usable_facts = [f for f in sources if f["value"]["normalized"] not in {"UNKNOWN",None,""}]
        if not usable_facts:
            resolved[kind]={"value":"UNKNOWN","state":"UNKNOWN","source_type":None,"confidence":None,"fact_ids":[f["id"] for f in sources]}
            continue
        ordered = sorted(usable_facts,key=lambda f:(SOURCE_PRIORITY[f["source_type"]],f["confidence"] or 0),reverse=True)
        chosen = ordered[0]
        value = chosen["value"]["normalized"]
        disagree = [f for f in ordered[1:] if str(f["value"]["normalized"]).casefold()!=str(value).casefold()]
        state = chosen["resolution_state"]
        if disagree:
            strong = [f for f in disagree if f["confidence"] is None or f["confidence"]>=.60]
            state = "CONFLICTING" if strong else "REVIEW_REQUIRED"
            conflicts.append({"fact_type":kind,"state":state,"preferred_value":value,
                "sources":[{"fact_id":f["id"],"value":f["value"]["normalized"],"raw":f["value"]["raw"],"source_type":f["source_type"]} for f in ordered],
                "reason":"Sources disagree. Priority selects the displayed value but does not remove competing evidence."})
        resolved[kind]={"value":value,"state":state,"source_type":chosen["source_type"],
                        "confidence":chosen["confidence"],"fact_ids":[f["id"] for f in sources]}
    for kind,sources in grouped.items():
        if kind not in resolved:
            f=sources[0]
            resolved[kind]={"value":f["value"]["normalized"],"state":f["resolution_state"],
                            "source_type":f["source_type"],"confidence":f["confidence"],"fact_ids":[f["id"]]}
    evidence = sufficiency(bundle,usable,ocr_state,conflicts,declaration_conflicts)
    states = [v["state"] for v in resolved.values()]
    overall = "CONFLICTING" if any(c["state"]=="CONFLICTING" for c in conflicts) else "REVIEW_REQUIRED" if "REVIEW_REQUIRED" in states else "UNKNOWN" if "UNKNOWN" in states else "INFERRED" if "INFERRED" in states else "KNOWN"
    # Never pass a disputed preferred value as a bare authoritative rule input.
    context_keys = {KEYS[k]:v for k,v in resolved.items()}
    context_keys["evidence.sufficiency"]={"value":evidence["state"],"state":"KNOWN","fact_ids":[]}
    return {"facts":facts,"resolved":resolved,"conflicts":conflicts,"resolution_status":overall,
            "evidence":evidence,"context_keys":context_keys,"applicability":preview(resolved)}

def sufficiency(bundle,usable,ocr_state,conflicts,declaration_conflicts):
    images=bundle["images"]
    reasons=[]
    failed_critical = any(i["panel"] in {"DECLARATION_PANEL","MRP_PANEL"} and
        not any(r["image_id"]==i["id"] and r["status"]=="SUCCESS" for r in usable) for i in images)
    unusable_quality = any(i["quality"] in {"UNREADABLE","PROCESSING_FAILED"} for i in images)
    if not images or not usable or failed_critical or unusable_quality:
        state="INSUFFICIENT"
        reasons.append("Missing usable OCR, failed critical-panel OCR, or unreadable evidence.")
    elif conflicts or declaration_conflicts or any(c["needs_review"] for c in bundle["candidates"]) or ocr_state in {"LOW","REVIEW"} or any(i["quality"]=="POOR" for i in images):
        state="REVIEW_REQUIRED"
        reasons.append("Context conflicts, low OCR confidence, or poor image quality require review.")
    elif (not bundle["extraction_run_id"] or bundle["extraction_status"]!="SUCCESS" or
          len(usable)<len(images) or any(r["status"]!="SUCCESS" for r in usable) or
          ocr_state=="UNKNOWN" or any(i["quality"] in {None,"PENDING"} for i in images)):
        state="PARTIAL"
        reasons.append("Extraction, OCR coverage, or image quality assessment is incomplete.")
    else:
        state="SUFFICIENT_FOR_RULE_EVALUATION"
        reasons.append("Uploaded evidence has quality assessment, usable OCR, and a current successful extraction.")
    reasons.append("Technical readiness only; package-panel completeness and legal absence are not established.")
    return {"state":state,"reasons":reasons,"image_count":len(images),"usable_ocr_images":len(usable),
            "ocr_confidence_state":ocr_state,"extraction_available":bool(bundle["extraction_run_id"])}

