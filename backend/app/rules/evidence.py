def evidence_links(evaluation,snapshot):
    links=[]
    role="CONTRADICTING" if evaluation["reason_code"]=="CONFLICTING_CANDIDATES" else "SUPPORTING"
    for candidate in snapshot["declarations"]:
        if candidate["id"] not in evaluation["candidate_ids"]: continue
        links.append({"evidence_type":"DECLARATION","declaration_candidate_id":candidate["id"],
                      "inspection_image_id":candidate["source_image_id"],"evidence_role":role,"detail":candidate})
        for block in candidate["sources"]:
            links.append({"evidence_type":"OCR_BLOCK","declaration_candidate_id":candidate["id"],
                "inspection_image_id":candidate["source_image_id"],"ocr_block_id":block["ocr_block_id"],
                "evidence_role":role,"detail":block})
    for fact in snapshot["facts"]:
        if fact["id"] in evaluation["context_fact_ids"]:
            links.append({"evidence_type":"CONTEXT_FACT","context_fact_id":fact["id"],"evidence_role":"CONTEXT","detail":fact})
    missing=not evaluation["candidate_ids"]
    for image in snapshot["source_inputs"]["images"]:
        links.append({"evidence_type":"IMAGE","inspection_image_id":image["id"],
            "evidence_role":"MISSING_EXPECTED" if missing and evaluation["verdict"]!="NOT_APPLICABLE" else "CONTEXT","detail":image})
    links.append({"evidence_type":"COVERAGE","evidence_role":"CONTEXT","detail":{
        "evidence":snapshot["evidence"],"ocr":snapshot["source_inputs"]["ocr"],
        "extraction_status":snapshot["source_inputs"]["extraction_status"],
        "note":"Absence results cite inspected coverage, never fabricated declaration coordinates."}})
    return links

