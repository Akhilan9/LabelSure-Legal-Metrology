# Rule engine design

Design only in Phase 0/1. No operational legal rules are shipped. The supplied 2011 document is source material for later verification, not evidence of current amendment coverage.

## Contract and separation

`evaluate(declarations, context, image_quality, coverage, rule_version, inspection_date) -> findings`

1. Load an explicit verified rule version applicable to the inspection date. Unknown versions, conflicting effective intervals or invalid definitions are configuration failures, not compliance PASS.
2. Determine applicability using three-valued logic: applicable, inapplicable, unknown. Missing context produces UNCERTAIN; only confirmed inapplicability produces NOT_APPLICABLE.
3. Resolve declarations and their provenance. Evidence quality and panel completeness determine whether absence can be asserted.
4. Dispatch to a validator registry keyed by the JSON `validation.type`. Unknown validators fail validation when loading the corpus. Do not execute arbitrary code from JSON.
5. Return one of PASS, FAIL, UNCERTAIN, NOT_APPLICABLE, with the exact rule snapshot and evidence supporting the decision.

AI extraction and frontend code never contain clause-specific conditions. Adding a rule using an existing validator needs only a validated rule definition. A new validation kind requires a new independently tested validator, without changes to OCR or UI contracts.

## Illustrative definition — not an active verified rule

```json
{
  "rule_id": "LM-R6-MRP",
  "rule_version": "draft-unverified",
  "clause_reference": "Rule 6 — exact subclause pending verification",
  "requirement": "Retail sale price declaration",
  "applicability": {"all": [{"field": "sale_channel", "equals": "retail"}]},
  "validation": {"type": "declaration_required", "declaration": "MRP"},
  "severity": "HIGH",
  "effective_from": null,
  "effective_to": null,
  "source": "User-supplied Legal Metrology document; verification pending",
  "verification_status": "DRAFT"
}
```

Drafts cannot enter verified evaluation. Effective intervals use `[effective_from, effective_to)` with an open upper bound allowed. Published metadata includes source URL/document hash, exact clause, effective dates, reviewer, verification date and definition hash. Severity is application prioritization, not an invented statutory penalty. Never claim that an MVP corpus establishes compliance with all Indian law.

## Validator families planned

Presence, alternative declarations, normalized value/unit/format, required wording, grouped contact fields, panel placement and calibrated physical measurement. Precise parameters come from verified sources in Phase 8. Support all requested declaration types without assuming every one applies to every product.

| Evidence/context | Result |
|---|---|
| Known inapplicability | NOT_APPLICABLE |
| Unknown applicability | UNCERTAIN |
| Blurry/unreadable or incomplete panel set | UNCERTAIN |
| Reliable, relevant declaration satisfies encoded requirement | PASS |
| Reliable observed value contradicts encoded requirement | FAIL |
| Absence reliably established across necessary panels with sufficient verification | FAIL |
| OCR did not detect a declaration, absence not established | UNCERTAIN |
| Physical scale unavailable | Measurement UNVERIFIED; affected compliance finding UNCERTAIN |

Readability and physical font height are separate. OCR confidence is not legal certainty. Preserve native confidence and its model/source; use null when absent. Do not invent a combined confidence. Calibrated measurements must retain reference geometry, transform, scale and uncertainty.

## Explainability and review

Each finding retains requirement, expected/observed values, status, rationale, raw OCR, original-image references and boxes, rule ID/version/source, model versions and later reviews. Absence findings reference coverage evidence rather than fabricated text coordinates. Inspector actions append records; original findings remain untouched.

Overall automated assessment is preliminary: any supported FAIL means potential NON_COMPLIANT; otherwise any unresolved applicable uncertainty means UNCERTAIN; all applicable rules passing permits COMPLIANT only within the evaluated corpus. All-NOT_APPLICABLE or empty rule selection means no assessment, not universal compliance. Final inspector assessment is separate and cannot be finalized while required review/rescan work remains unresolved.

## Tests required in Phase 8

Use verified fixtures for all four outcomes, missing context, low-confidence text, incomplete coverage, malformed rules, unknown validator types, effective-date boundaries, conflicting versions, no applicable rules and measurement without calibration. Test reproducibility against frozen input/rule/model snapshots. Measure false positives on ambiguous images and record real metrics only.

## Phase 7 implementation boundary

Phase 7 implements context preparation only. The illustrative rule above is still unverified and is not executed. No operational verified statutory conditions were found in this repository. All preview rows therefore carry TODO_LEGAL_VERIFICATION and executable=false.

Stable input keys:
- package.import_status, package.type, package.country_of_origin
- product.category
- quantity.kind
- evidence.sufficiency, evidence.ocr_available, evidence.ocr_confidence_state
- declaration.mrp.detected, declaration.net_quantity.detected
- declaration.manufacturer.detected, declaration.packer.detected, declaration.importer.detected
- declaration.consumer_care.detected, declaration.month_year.detected
- declaration.common_name.detected, declaration.country_of_origin.detected
- declaration.conflict_present

Each key stores value and resolution state; relevant keys also store source type/confidence and fact IDs. Conflicting preferred values must not be treated as confirmed facts by Phase 8. Detection false means no candidate detected; null means current extraction is unavailable.

Preparatory identifiers: DECLARATION_COMMON_NAME, DECLARATION_MANUFACTURER, DECLARATION_PACKER, DECLARATION_NET_QUANTITY, DECLARATION_MRP, DECLARATION_IMPORTER, DECLARATION_CONSUMER_CARE, DECLARATION_MONTH_YEAR, DECLARATION_COUNTRY_OF_ORIGIN. They are not verified rule definitions.

For the user-requested importer illustration, KNOWN imported context gives POTENTIALLY_APPLICABLE, KNOWN domestic gives NOT_APPLICABLE_BY_CONTEXT, and inferred/unknown/disputed context gives APPLICABILITY_UNCERTAIN. Even the domestic/imported hint remains unverified and non-executable. Other identifiers remain APPLICABILITY_UNCERTAIN until verified legal conditions exist. No candidate presence/absence is converted into a compliance result.

RuleInputSnapshot schema version 1 freezes inputs, OCR/candidate provenance, source facts, resolved states, evidence sufficiency, conflicts, and preview. Phase 8 must use an immutable snapshot ID/hash plus a verified rule version. Snapshot readiness does not verify necessary package-side coverage, law applicability, sector-specific obligations, or physical font size.

Context inference and applicability preparation are not legal verdicts. Sector-specific laws and calibrated font-size checks remain outside the implemented scope. Stop before Phase 8 until explicitly authorized.

