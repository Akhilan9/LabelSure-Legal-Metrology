"""Preparatory routing hints only. No verified statutory conditions exist in this repository."""
def preview(resolved):
    result = []
    keys = ["DECLARATION_COMMON_NAME","DECLARATION_MANUFACTURER","DECLARATION_PACKER",
            "DECLARATION_NET_QUANTITY","DECLARATION_MRP","DECLARATION_IMPORTER",
            "DECLARATION_CONSUMER_CARE","DECLARATION_MONTH_YEAR","DECLARATION_COUNTRY_OF_ORIGIN"]
    for key in keys:
        state = "APPLICABILITY_UNCERTAIN"
        reason = "Verified legal applicability conditions are not yet available."
        if key == "DECLARATION_IMPORTER":
            fact = resolved["IMPORT_STATUS"]
            if fact["state"] == "KNOWN" and fact["value"] in {"IMPORTED","DOMESTIC"}:
                state = "POTENTIALLY_APPLICABLE" if fact["value"] == "IMPORTED" else "NOT_APPLICABLE_BY_CONTEXT"
                reason = "Inspector-supplied context indicates " + fact["value"].lower() + " packaging; this is a preparatory context hint only."
            else:
                reason = "Import context is unknown, inferred, or requires review."
        result.append({"rule_key":key,"state":state,"reason":reason,
                       "verification_status":"TODO_LEGAL_VERIFICATION","executable":False})
    return result

