# Phase 7 completion report

Product/Package Context and Rule Applicability Preparation is implemented. No Phase 8 legal evaluation has been started.

## 1. Files created

- backend/app/models/context.py
- backend/app/context/__init__.py
- backend/app/context/service.py
- backend/app/context/resolver.py
- backend/app/context/facts.py
- backend/app/context/schemas.py
- backend/app/context/scoring.py
- backend/app/context/applicability.py
- backend/app/api/context.py
- backend/migrations/versions/0006_context.py
- backend/app/scripts/verify_context_live.py
- backend/tests/test_context.py
- backend/tests/test_context_migration.py
- frontend/src/components/ContextApplicability.jsx
- docs/PHASE7_COMPLETION.md

## 2. Files modified

- backend/app/models/__init__.py — register context models.
- backend/app/core/config.py — CONTEXT_PIPELINE_VERSION with length bounds.
- backend/app/main.py — register Phase 7 router.
- backend/.env.example — context version configuration.
- backend/tests/test_extraction_migration.py — update expected current migration head; retain preservation coverage.
- frontend/src/pages/InspectionDetail.jsx — context section and refresh coordination.
- frontend/src/components/ExtractedDeclarations.jsx — notify context view after extraction.
- docs/ARCHITECTURE.md
- docs/IMPLEMENTATION_PLAN.md
- docs/API_CONTRACT.md
- docs/DATABASE_SCHEMA.md
- docs/VERIFICATION.md
- docs/RULE_ENGINE_DESIGN.md
- README.md

The existing local database was upgraded after backup. Build output/test caches were regenerated. Project files were already untracked; no Git commit was made.

## 3. Database migration

0006_context follows 0005_extraction. It adds context_resolution_runs, inspection_contexts, context_facts, and rule_input_snapshots with foreign keys, controlled-state constraints, indexes, and unique resolution fingerprints. Preview items are stored in snapshots rather than a redundant table.

## 4. Context architecture

Inspection metadata + explicit inspector context + current extraction + latest OCR + image quality → source facts → resolved context/conflicts → technical evidence assessment → frozen rule-input snapshot → non-executable applicability preparation.

Dedicated modules separate HTTP handling, persistence, normalization, source priority, resolution, and preview. No LLM, vector store, GPU processing, or queue is introduced.

## 5. Context facts implemented

PRODUCT_CATEGORY, PACKAGE_TYPE, IMPORT_STATUS, COUNTRY_OF_ORIGIN, QUANTITY_KIND; HAS_MRP_CANDIDATE, HAS_NET_QUANTITY_CANDIDATE, HAS_MANUFACTURER_CANDIDATE, HAS_PACKER_CANDIDATE, HAS_IMPORTER_CANDIDATE, HAS_CONSUMER_CARE_CANDIDATE, HAS_MONTH_YEAR_CANDIDATE, HAS_COMMON_NAME_CANDIDATE, HAS_COUNTRY_OF_ORIGIN_CANDIDATE; OCR_EVIDENCE_AVAILABLE, OCR_CONFIDENCE_STATE, DECLARATION_CONFLICT_PRESENT.

Source facts retain raw/normalized value, references, source type, optional confidence, state, and explanation. Missing core context remains explicit in resolved output. Detection false means no candidate detected; null means no current extraction.

## 6. Resolution states

KNOWN, INFERRED, UNKNOWN, CONFLICTING, REVIEW_REQUIRED. Resolved values retain state, source, source confidence, and fact IDs. Preferred disputed values are never flattened into bare confirmed rule inputs.

## 7. Source priority

Reserved MANUAL_OVERRIDE > INSPECTOR_INPUT > INSPECTION_METADATA > DECLARATION_CANDIDATE > OCR_EVIDENCE > SYSTEM_INFERENCE.

Inspector-entered values use null confidence. Extracted context preserves native extraction confidence instead of inventing a combined probability. Explicit inputs are separate from metadata; omission retains saved input and null removes it.

## 8. Conflict handling

All competing source facts remain. Priority selects the displayed value; disagreement with a known or confidence >=0.60 source marks CONFLICTING. Weaker disagreement remains REVIEW_REQUIRED. Conflicts show raw evidence and provenance in the UI and snapshot. No automatic legal override occurs.

## 9. Quantity-kind resolution

g/kg → WEIGHT; ml/L → VOLUME; count/pcs/pieces → COUNT; m/cm/mm → LENGTH; m2/m² → AREA. Unsupported or unavailable units → UNKNOWN. Candidate evidence is linked; explicit inspector quantity input remains distinguishable.

## 10. Import-context handling

Foreign origin alone does not infer import status. Importer candidates produce a possible imported signal requiring review. Inspector DOMESTIC versus importer evidence remains a conflict. Confirmed inspector input is distinguishable from inference. Unresolved/disputed import state cannot produce a confirmed applicability hint.

## 11. Evidence-sufficiency logic

Missing usable OCR, unreadable/processing-failed evidence, or failed/missing critical-panel OCR → INSUFFICIENT. Conflicts, candidate review flags, weak OCR, or poor quality → REVIEW_REQUIRED. Incomplete extraction/OCR/quality assessment → PARTIAL. Otherwise technical readiness is SUFFICIENT_FOR_RULE_EVALUATION.

These states do not establish full physical panel coverage, legal absence, or compliance. OCR failure never produces a non-compliance decision.

## 12. RuleInputSnapshot implementation

Canonical JSON copies input metadata, explicit context, candidates and OCR source details, facts, resolved context, stable keys with resolution states, technical evidence, conflicts, and preview. SHA-256 fingerprinting supports input caching; content SHA-256 verifies immutable snapshot reads.

Snapshots have no mutation endpoint; ORM replacements are rejected. Context changes create new runs without modifying historical snapshots. Authorized snapshot_id queries read history. Phase 8 should bind evaluation to snapshot ID/hash and independently verified rule version.

## 13. Applicability-preview implementation

Nine stable preparatory declaration identifiers are exposed. Every item carries TODO_LEGAL_VERIFICATION and executable=false because the repository has no verified operational legal conditions.

The requested importer illustration distinguishes known domestic/imported context using NOT_APPLICABLE_BY_CONTEXT/POTENTIALLY_APPLICABLE. Unknown, inferred, or disputed context yields APPLICABILITY_UNCERTAIN. Other identifiers remain uncertain pending legal verification. These hints execute no statutory conditions and return no compliance verdict.

## 14. API endpoints

Under /api/v1:

- POST /inspections/{inspection_id}/resolve-context
- GET /inspections/{inspection_id}/context
- GET /inspections/{inspection_id}/context/facts
- GET /inspections/{inspection_id}/rule-input
- GET /inspections/{inspection_id}/applicability-preview

The rule-input endpoint accepts optional snapshot_id for authorized historical access. Context can resolve before extraction with explicit evidence limitations.

## 15. RBAC behavior

INSPECTOR resolves/views inspections they created; ADMIN resolves/views all; SUPERVISOR only reads. Missing authentication → 401; supervisor mutation → 403; inaccessible inspection/snapshot → 404. Snapshot IDs are always scoped to the requested inspection. Debug JSON UI is ADMIN-only; sanitized rule-input API is accessible to authorized viewers.

## 16. Frontend changes

Context & Applicability displays product/package context, source/state/confidence, evidence sufficiency, source facts, conflicts, and non-executable preview hints. Inspector input controls preserve separate source handling. ADMIN has an optional rule-input JSON view. Extraction completion refreshes context freshness. Existing styling and inspection layout are retained.

## 17. Tests added

53 Phase 7 cases cover metadata, inspector input, quantities, country/importer semantics, source provenance/priority, conflicts/review, detection versus absence, evidence sufficiency, OCR failure, weak OCR, image quality, snapshots/history/versioning, input reactivation, idempotency, authorization/IDOR, tampering, invalid input, secret/path exclusion, unchanged inspection state, and migration preservation.

Critical cases explicitly verify failed OCR → insufficient evidence, missing low-confidence candidates do not establish legal absence, importer evidence is not automatic confirmation, and imported context creates only an unverified preparation hint.

## 18. Total backend test result

**216 passed, 6 warnings in 88.24 seconds.** All 163 prior tests remain covered, including real PaddleOCR CPU inference. After a final timestamp correction, **all 53 Phase 7 cases passed again in 16.08 seconds**.

## 19. Frontend build result

**npm.cmd run build passed.** 112 modules transformed; JavaScript 385.04 kB (117.37 kB gzip); CSS 40.02 kB (8.80 kB gzip). No build errors.

## 20. Migration verification

Fresh migration and populated Phase 6 upgrade passed. The populated test preserves users, inspections, images, OCR runs/blocks, extraction runs, candidates, and candidate sources through upgrade, downgrade, and re-upgrade. Alembic check found no new upgrade operations.

Local database: 0005_extraction → 0006_context. Backup: backend/.pytest_cache/phase6_before_context.db. All existing rows were compared unchanged: 3 users, 1 inspection, 2 images; other local evidence tables were empty.

## 21. Live end-to-end verification

verify_context_live.py runs real loopback HTTP with disposable database/storage and controlled MockOCR: login → create/upload → image quality processing → OCR → extraction → context → snapshot digest → preview → repeat-resolution equality.

Final observation: 9 candidates, 17 facts, quantity WEIGHT, import DOMESTIC, context REVIEW_REQUIRED, evidence INSUFFICIENT under the synthetic image's quality assessment. This technical limitation was retained; no legal decision was produced. Snapshot integrity and idempotency passed. Resolution HTTP latency: **93.61 ms** for this local controlled fixture.

## 22. Security checks

Tested unauthenticated/cross-inspector denial, supervisor write denial, historical snapshot scoping, arbitrary internal-key rejection, enum/string/control-Unicode validation, snapshot replacement prevention, direct database corruption detection, and exclusion of internal paths/credentials from projected snapshots. React renders untrusted values as escaped text. Candidate inputs are capped at 1,000/2 MB serialized; snapshots at 5 MB; explicit text input at 100 characters.

## 23. Known limitations/warnings

- Context inference and applicability preview are not legal verdicts.
- Extracted context may be wrong because OCR/extraction may be wrong.
- Candidate absence does not prove declaration absence.
- Unknown/conflicting context remains explicit.
- No operational legal conditions are verified or executed in this phase.
- Sector-specific laws, physical font-size compliance, finalization, overrides, and compliance reports are not implemented.
- Evidence sufficiency describes the uploaded evidence, not proven coverage of every relevant package side.
- Source confidence thresholds are engineering heuristics, not calibrated legal certainty.
- Unexpected resolution failures roll back; persistent FAILED-run diagnostics are reserved for later observability.
- Hash checks detect snapshot alteration; they do not replace database access controls.
- Historical Phase 5 derived-image versioning limitations remain unchanged.
- Interactive browser validation, PostgreSQL runtime migration, and production load testing were not performed.
- Six full-suite warnings concern existing dependency deprecations and optional Paddle ccache availability.

Stop here. Wait for **Continue to Phase 8.**

