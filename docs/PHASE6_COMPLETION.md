# Phase 6 completion report

Phase 6 — Structured Declaration Extraction is implemented. Phase 7 has not started.

## 1. Files created

- backend/app/models/extraction.py
- backend/app/extraction/__init__.py
- backend/app/extraction/engine.py
- backend/app/extraction/service.py
- backend/app/extraction/patterns.py
- backend/app/extraction/normalizers.py
- backend/app/extraction/spatial.py
- backend/app/extraction/scoring.py
- backend/app/extraction/schemas.py
- backend/app/api/extraction.py
- backend/migrations/versions/0005_extraction.py
- backend/app/scripts/verify_extraction_live.py
- backend/tests/test_extraction.py
- backend/tests/test_extraction_migration.py
- frontend/src/components/ExtractedDeclarations.jsx
- docs/PHASE6_COMPLETION.md

## 2. Files modified

- backend/app/models/__init__.py — register models.
- backend/app/core/config.py — bounded EXTRACTION_PIPELINE_VERSION setting.
- backend/app/main.py — register extraction routes.
- backend/.env.example — document extraction version configuration.
- frontend/src/pages/InspectionDetail.jsx — integrate declarations section.
- README.md
- docs/ARCHITECTURE.md
- docs/IMPLEMENTATION_PLAN.md
- docs/API_CONTRACT.md
- docs/DATABASE_SCHEMA.md
- docs/VERIFICATION.md

The existing local SQLite database was upgraded after backup. Frontend build output and test caches were regenerated. The workspace's project files were already untracked; no commit was created.

## 3. Database migration

0005_extraction follows 0004_ocr and adds extraction_runs, declaration_candidates, declaration_candidate_sources. Existing evidence tables and data are preserved. Enum checks, foreign keys, lookup indexes, and a unique extraction snapshot constraint are included.

## 4. Extraction architecture

API → ExtractionService → bounded deterministic engine → pattern/normalizer/spatial/scoring modules → transactional persistence. Latest OCR evidence per image is used. No external LLM, API key, or background worker is required.

## 5. Declaration types supported

COMMON_PRODUCT_NAME; MANUFACTURER_NAME; MANUFACTURER_ADDRESS; PACKER_NAME; PACKER_ADDRESS; IMPORTER_NAME; IMPORTER_ADDRESS; NET_QUANTITY; MRP; MONTH_YEAR; COUNTRY_OF_ORIGIN; CONSUMER_CARE_NAME; CONSUMER_CARE_ADDRESS; CONSUMER_CARE_PHONE; CONSUMER_CARE_EMAIL; BARCODE_OR_GTIN; UNIT_SALE_PRICE; OTHER.

OTHER requires an explicit label. Product name requires a label or an exact front-panel OCR match to inspector context.

## 6. Normalizers/parsers

Unicode NFKC and control cleanup operate on a working copy. Decimal money retains INR and two decimal places. Quantity aliases normalize without magnitude conversion. Unambiguous month/year values normalize; two-digit years require review without inventing a century. Country and organizations remain observed text. Contextual email/phone parsing and GTIN length/check-digit validation are deterministic.

## 7. Confidence scoring

0.55 × minimum supporting OCR confidence + keyword contribution (0.20, heuristic 0.10) + format (0.15, heuristic/ambiguous 0.05) + accepted spatial context (0.05) + relevant panel (0.05). Clamp to 0–1. Contributions are stored and shown. Below 0.80 requires review; heuristics and ambiguous dates also require review. Scores are not calibrated probabilities.

## 8. Multi-block extraction

A label can use up to four nearby following OCR blocks. Same-row and vertically aligned proximity checks stop distant merges. New declaration labels terminate context. Organization name/address and consumer-care detail fixtures exercise ordered supporting blocks.

## 9. Provenance implementation

Each candidate references inspection, extraction run, OCR run, image, first OCR block, and ordered source-block relationships. Raw value preserves exact supporting OCR text. Candidate detail exposes original source text, polygons, and boxes. The viewer uses existing authorized image endpoints.

## 10. Duplicate/conflict behavior

Identical values on different blocks/images remain separate. One highest-confidence primary is chosen only without strong disagreement. Different normalized values with scores ≥0.80 mark the entire type for review; none is primary. New OCR, panel, product context, or extraction version produces a fresh snapshot. Old candidates are not shown as current.

## 11. API endpoints

Under /api/v1:

- POST /inspections/{inspection_id}/extract-declarations
- GET /inspections/{inspection_id}/declarations
- GET /inspections/{inspection_id}/declarations/{candidate_id}
- GET /inspections/{inspection_id}/extraction-summary

List supports offset/limit. Missing usable OCR returns 409. Oversized evidence returns 422. Current summary is null before extraction or after evidence changes.

## 12. RBAC behavior

INSPECTOR runs/views only inspections they created. ADMIN runs/views all. SUPERVISOR has read-only access. Missing authentication is 401, forbidden supervisor mutation is 403, and inaccessible inspection/candidate objects are 404.

## 13. Frontend changes

Inspection Detail includes Extracted Declarations with type, value, confidence, panel/image, method, primary marker, and review reasons. Conflict notices retain competing values. Evidence selection displays source image, all supporting boxes, raw OCR text, and confidence contributions. Existing design classes and the OCR viewer are reused.

## 14. Tests added

63 cases across test_extraction.py and test_extraction_migration.py cover all required parser categories, negative/contextual examples, raw preservation, source linkage, spatial boundaries, confidence, duplicate/conflict behavior, cross-panel evidence, RBAC/IDOR, idempotency/version changes, stale/failed OCR, preconditions, bounded payloads, inspection-state preservation, performance, and migration behavior.

## 15. Total backend test result

**163 passed, 6 warnings in 66.70 seconds.** All 100 existing tests remain and pass, including real PaddleOCR CPU inference. Warnings concern dependency deprecations and optional ccache.

## 16. Frontend build result

**npm.cmd run build succeeded.** 111 modules transformed. JavaScript bundle: 377.52 kB, gzip 115.17 kB. No build errors.

## 17. Migration verification

Fresh migration, populated Phase 5 upgrade, downgrade/re-upgrade, and Alembic metadata comparison passed. The local database was upgraded from 0004_ocr to 0005_extraction after backup to backend/.pytest_cache/phase5_before_extraction.db. All existing rows were unchanged: 3 users, 1 inspection, 2 images. Local OCR tables were empty; a separate populated fixture verified OCR text and image hashes survive. Alembic check found no new upgrade operations. PostgreSQL runtime verification was not performed.

## 18. Live extraction verification

verify_extraction_live.py starts a real loopback HTTP server with disposable database/storage and controlled MockOCR evidence. Login → inspection → synthetic image upload → OCR → extraction → evidence/detail retrieval → repeat-call cache verification passed.

The requested masala fixture produced nine candidates: product name, quantity, MRP, manufacturer name/address, month/year, consumer phone/email, country. All candidates had source linkage.

## 19. Security checks

Tested unauthenticated access, cross-inspector denial, supervisor write denial, candidate-ID scoping, oversized OCR rejection, raw evidence preservation, malformed/control Unicode cleanup, and contextual false-positive rejection. React escapes displayed text. Patterns and neighboring-block windows are bounded. Limits: 5,000 blocks, 2,048 characters per block, 1,000 candidates. No OCR text is executed or sent to an external service.

## 20. Performance observations

Controlled live extraction HTTP call took **70.22 ms** for the 12-block synthetic fixture. A 1,000-block unrelated-text test meets a three-second bound. These are local observations, not throughput or production-scale benchmarks. No new worker infrastructure was added.

## 21. Known limitations

- Candidates do not establish legal compliance.
- OCR errors may propagate; low confidence requires review.
- Missing candidates do not prove declarations are absent.
- Company/address/country parsing is heuristic; product-name extraction is conservative.
- Two-digit date years retain century ambiguity.
- Multiple legitimate contact/date values can trigger conservative conflict review.
- No multilingual semantic parser, barcode vision, manual verification workflow, rule execution, or compliance report is provided.
- Historical Phase 5 derived images are not separately versioned; later reprocessing can change the displayed derived artifact. Original evidence and OCR-block provenance remain intact.
- The frontend build passed; an interactive browser audit was not performed.
- Completed extraction calls persist atomically as SUCCESS/PARTIAL. Unexpected errors roll back instead of retaining a FAILED run.
- PostgreSQL runtime verification and production load testing remain unperformed.

Stop here. Continue only on the explicit instruction: **Continue to Phase 7.**

