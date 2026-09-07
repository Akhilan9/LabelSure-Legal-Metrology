# Verification history

## Phase 5

Verified on 7 September 2026 on Windows 10 (Python 3.13.5, Node 22.12 / Vite 7.3.6).

## Executed Results

| Command / check | Actual result |
|---|---|
| `pytest -v` (backend cwd) | **100 passed, 6 warnings in 59.63s**, exit 0 |
| `npm.cmd run build` (frontend cwd) | **PASS**, Vite 7.3.6, 110 modules transformed, exit 0 (3.47s) |
| `alembic upgrade head` | **PASS**, Revisions `0001_users`, `0002_inspections`, `0003_image_quality`, `0004_ocr` applied cleanly |
| Live API verification suite | **PASS**: Text recognition, polygon bounding boxes, reading order, confidence tiers, batch OCR, multi-panel summary, RBAC, and IDOR protection |
| Real PaddleOCR CPU inference smoke test | **PASS** (`test_paddle_ocr_real.py`), Real deep-learning inference recognizing commodity package tokens (`QUANTITY`, `500`, `MRP`, `150`) on CPU |
| Python environment integrity (`pip check`) | **PASS**, `paddleocr 3.7.0`, `paddlepaddle 3.3.0`, `opencv-python-headless 5.0.0.93`, `numpy 2.5.3`, `pillow 12.3.0` installed without dependency conflicts |
| Evidence immutability audit | **PASS**, Original evidence files untouched; derived preprocessed artifacts and OCR runs maintain full relational traceability |

## Test Suite Breakdown (100 total tests)

- `test_auth.py` (37 tests): JWT issuance, claims, token tampering, Argon2 password verification, role checks, dev route isolation, secret enforcement.
- `test_inspections.py` (7 tests): Inspection creation, optional product context, sequential code generation (`INS-2026-XXXXXX`), unauthenticated rejection, supervisor creation prohibition, cross-inspector isolation (IDOR defense), admin visibility, and search/filter queries.
- `test_images.py` (8 tests): Single image upload, multiple images with panel mapping, magic byte validation (JPEG, PNG, WebP), zero-byte rejection, oversized file rejection, image count limits, streaming content with Bearer auth, panel updates, evidence deletion with status rollback, supervisor read-only streaming, cross-inspector access rejection.
- `test_submission.py` (4 tests): Rejection of submissions without evidence (422), successful submission transitioning to `READY_FOR_ANALYSIS`, post-submission modification blocking (409 Conflict), RBAC enforcement during submission.
- `test_image_quality.py` (8 tests): Unit quality calculation of focus (variance of Laplacian), mean luminance, contrast standard deviation, glare saturation ratio, minimum resolution check, empty/corrupt image handling, EXIF orientation handling, and packaging-specific CLAHE pre-processing preservation.
- `test_image_processing.py` (6 tests): End-to-end single image processing pipeline, processing idempotency with version tagging (`processing_version="1"`), batch processing endpoint, image quality retrieval endpoint, RBAC and IDOR enforcement, and corrupt file failure tracking.
- `test_ocr_provider.py` (8 tests): Unicode NFKC text normalization, statutory character and number preservation, polygon bounding box calculation, empty polygon handling, confidence tier mapping (`GOOD`, `REVIEW`, `LOW`), spatial reading order sorting with vertical proximity grouping, MockOCRProvider execution, MockOCRProvider simulated failure handling, and PaddleOCRProvider properties.
- `test_ocr.py` (6 tests): Single image OCR end-to-end integration, idempotency caching with `ocr_version="1"` and `force=true` bypass, batch OCR execution and multi-panel summary aggregation, OCR blocks endpoint, RBAC and IDOR cross-inspector isolation, and OCR provider failure handling with error code capture.
- `test_paddle_ocr_real.py` (1 test): Live CPU smoke test executing real deep-learning inference on synthetic package evidence images using `PaddleOCRProvider` with PP-OCRv6.
- `test_storage.py` (5 tests): Content-based magic byte detection, SHA-256 calculation, local storage directory hierarchy (`storage/inspections/<id>/originals/` and `storage/inspections/<id>/processed/`), path traversal prevention (`_resolve_safe_path`).
- `test_dashboard.py` (1 test): Real inspection count metrics, role scoping (inspector vs admin).
- `test_health.py` (6 tests): Database connection verification, 503 on database unavailability, CORS policy enforcement, future feature exclusion.
- `test_migrations_seed.py` (2 tests): Alembic migration idempotent runs and dev seed guardrails.

## Frontend UI Deliverables
- `frontend/src/components/OCRBoundingBoxCanvas.jsx`: Interactive SVG coordinate visualizer rendering bounding polygons on top of evidence images with confidence tier color coding (`GOOD` emerald, `REVIEW` amber, `LOW` rose), reading order badges, and hover/click selection callbacks.
- `frontend/src/components/OCRBlockTable.jsx`: Structured text block table displaying recognized lines in reading order with search filtering, confidence tier filter buttons, and clipboard copy.
- `frontend/src/components/InspectionOCRSummarySection.jsx`: Multi-panel inspection OCR text summary tab with per-panel text extracts and copy actions.
- `frontend/src/pages/InspectionDetail.jsx`: Integrated single and batch OCR action triggers, tabbed modal displaying the interactive OCR bounding box viewer alongside preprocessed image comparisons, and panel-level OCR status chips.
- `frontend/src/pages/NewInspection.jsx`: 4-step wizard for Product Information, Package Image Upload with drag-and-drop & camera support, Evidence Review, and Submission.
- `frontend/src/pages/InspectionsList.jsx`: Inspection history table with search query filtering, status tabs, pagination, and empty state.
- `frontend/src/App.jsx`: Real dashboard metric cards and recent inspections table.
- `frontend/src/components/AuthorizedImage.jsx`: Secure client-side authenticated blob loader for protected original and derived image streaming with `onLoad` dimension callbacks.

## Security and Engineering Controls Verified
1. **AI Observes, Rules Decide**: OCR is strictly an evidence observation stage. OCR outputs generate zero regulatory compliance verdicts (`PASS`/`FAIL`). Low confidence or OCR failures are logged as technical observations, never legal violations.
2. **Evidence Immutability & Traceability**: Original evidence images remain untouched; OCR runs operate on derived OCR-ready preprocessed artifacts while maintaining strict relational links back to original evidence.
3. **Deterministic Normalization**: Preserves immutable `raw_text` for legal evidence while providing `normalized_text` (Unicode NFKC, non-breaking space replacement, whitespace collapsing) without altering statutory numbers, symbols, or spelling.
4. **Idempotency & Versioning**: OCR requests record an `ocr_version` (default `"1"`). Re-running OCR on an image without `force=true` returns existing cached results.
5. **Path Traversal Defense**: `LocalStorageService` resolves storage paths against an absolute base directory and rejects any attempted path traversal.
6. **IDOR & Isolation**: Non-owner inspectors receive HTTP 404 on private inspection/OCR endpoints to prevent object existence enumeration.
7. **Role-Based Access Control**: Supervisors are restricted to read-only access on OCR runs and summaries, while Inspectors can only run OCR processing on their own inspections.

## Phase 6 verification — 2026-09-07

Reproducible commands from backend:
```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m app.scripts.verify_extraction_live
```
Frontend: `npm.cmd run build`.

Phase 5 regression run: 100 passed, including real PaddleOCR CPU inference. Phase 6 tests cover MRP/unit/date variants, country labels, manufacturer/packer/importer, multiline addresses, consumer contacts, product context, GTIN checks, source preservation, false positives, confidence, bounded input, cross-panel duplicates, conflicts, RBAC/IDOR, version/snapshot caching, missing/failed OCR, partial panels, unchanged inspection status, and migration preservation. The negative "MRP -5" test exposed a separator ambiguity, which was fixed before final verification.

Live verification uses a disposable database/storage directory and a real loopback Uvicorn HTTP server with controlled MockOCR evidence. It logs in, creates an inspection, uploads a synthetic image, runs OCR, extracts candidates, reads candidate detail/image evidence, and checks repeat-call idempotency. It extracted nine candidate types from the requested masala fixture: product name, quantity, MRP, manufacturer name/address, month/year, consumer phone/email, and country. Observed extraction HTTP latency: 70.22 ms in this environment; this is a single controlled measurement, not a production benchmark.

Local database migration: 0004_ocr → 0005_extraction. Backup: backend/.pytest_cache/phase5_before_extraction.db. All existing rows were unchanged: 3 users, 1 inspection, 2 images; local OCR and processing tables were empty. The migration test separately upgrades populated OCR evidence and verifies raw OCR text and image SHA-256 survive. Alembic check reported no new upgrade operations.

Security checks include authentication, cross-inspector object denial, supervisor mutation denial, candidate-ID scoping, raw-text preservation, contextual false-positive rejection, control/Unicode normalization, and oversized OCR rejection. UI uses escaped React text nodes. A full browser interaction audit and PostgreSQL runtime migration were not performed; frontend compilation and SQLite migration verification were performed.


Final Phase 6 backend result: **163 passed, 6 warnings in 66.70 seconds** (100 prior tests + 63 new cases). Warnings are dependency deprecations and Paddle's missing optional ccache notice. Frontend: **111 modules transformed; production build succeeded**, 377.52 kB JavaScript (115.17 kB gzip).

## Phase 7 verification — 2026-09-07

Backend full regression: **216 passed, 6 warnings in 88.24 seconds**, comprising all 163 prior cases and 53 new Phase 7 cases. The Phase 6 migration assertion was updated for the new head without removing its preservation checks. Real PaddleOCR CPU inference remains in the full suite.

Phase 7 cases cover metadata normalization, explicit import input, quantity kinds, foreign origin without import inference, importer review signals, source priority/conflicts, detection-only semantics, evidence readiness, OCR failure, weak OCR, quality handling, stable keys, deterministic resolution, API snapshot generation, history/version/cache reactivation, RBAC/IDOR, input constraints, snapshot corruption, secret/path exclusion, and inspection-status preservation. The populated migration fixture preserves Phase 6 OCR, candidates, and ordered sources.

Frontend `npm.cmd run build` succeeded: 112 modules; JavaScript 385.04 kB (117.37 kB gzip), CSS 40.02 kB (8.80 kB gzip).

Live script:
```powershell
# From backend
.venv/Scripts/python.exe -m app.scripts.verify_context_live
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
```

The live script uses a disposable SQLite database, real loopback Uvicorn HTTP, synthetic package image, and deterministic MockOCR. It performs login, inspection/upload, image processing, OCR, extraction, context resolution, snapshot digest verification, preview, and repeated-resolution/snapshot equality checks.

Observed result: 9 candidates, 17 source facts, WEIGHT quantity kind, DOMESTIC import context; overall REVIEW_REQUIRED and technical evidence INSUFFICIENT under the existing synthetic image-quality assessment. This is intentionally retained, not converted into a legal decision. Context HTTP resolution took 93.61 ms on the final live run. All preview items were non-executable; no legal rules ran.

Local migration: 0005_extraction → 0006_context. Backup: backend/.pytest_cache/phase6_before_context.db. Every existing row was unchanged (3 users, 1 inspection, 2 images; other local evidence tables empty). A populated fixture separately verified OCR/extraction/source preservation. Alembic check reported no new upgrade operations.

Security verification includes unauthenticated and cross-inspector denial, supervisor write denial, snapshot-ID scoping, unknown internal-key rejection, Unicode/control/length checks, immutable snapshot replacement prevention, read-time digest failure on direct database corruption, and absence of internal paths/credentials in the snapshot projection. No interactive browser audit, PostgreSQL runtime migration, or production load benchmark was performed. Dependency warnings are unchanged deprecations and optional Paddle ccache availability.


Final timestamp correction recheck: all **53 Phase 7 tests passed in 16.08 seconds**. The live script also explicitly recomputed the stored snapshot digest and passed.
