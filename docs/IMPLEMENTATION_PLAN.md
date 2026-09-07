# Implementation plan

## Delivery gate

Phases 0–7 are implemented. Stop after Phase 7 verification. Phase 8 requires the explicit instruction: **Continue to Phase 8.**

| Phase | Deliverables | Acceptance gate |
|---|---|---|
| 0 | Architecture, implementation plan, API contract, database schema, rule-engine design | Scope and interfaces documented; future work distinguished |
| 1 | React/Vite/Tailwind shell; FastAPI; settings; SQLAlchemy; CORS; health; Docker | Frontend builds, backend tests pass, real HTTP health responds |
| 2 | Migrations, User/Role, password hashing, JWT, RBAC | Login success/failure, expiry, disabled users and forbidden access tested |
| 3 | Product, Inspection, multiple images, local storage, workflow | Multi-image upload, magic bytes, SHA-256, panel assignment, submission lock, 71 tests pass |
| 4 | Quality and OpenCV preprocessing | Explainable blur/brightness/contrast/glare metrics, LAB CLAHE enhancement, bilateral denoising, derived artifact isolation, 85 tests pass |
| 5 | PaddleOCR adapter & Evidence Text Extraction | Real CPU inference on synthetic package evidence, provider abstraction, MockOCR test fixtures, OCRRun/OCRBlock ORM models, migration 0004_ocr, statutory normalization, spatial reading order, bounding box SVG viewer, 100 tests pass |
| 6 | Complete: deterministic declaration extraction, provenance, API and evidence UI | Per-type fixtures, RBAC, caching, conflicts, migration preservation, live HTTP extraction and frontend build |
| 7 | Complete: product/package context, source facts, immutable rule inputs and applicability preparation | Known/unknown/conflicting context, source priority, technical sufficiency, snapshot history, authorization and migration preservation verified |
| 8 | Verified MVP rule corpus, versions, applicability, validators | PASS/FAIL/UNCERTAIN/NOT_APPLICABLE fixtures; date/version boundaries tested |
| 9 | RuleLens and evidence UI | Findings expose source image, box, rule snapshot, confidence and reasoning |
| 10 | Inspector review, cases, audit, finalization | Append-only reviews; AI result preserved; permissions and finalization enforced |
| 11 | PDF, JSON/CSV exports | Authorized files match final snapshots and include evidence and review status |
| 12 | Repository, dashboard, search/filter, trends | Real persisted data, pagination and explicit metric denominators |
| 13 | Integration, usability, deployment, measured demo set | Compliant, violation, ambiguous, failed-service and poor-image scenarios |

## Dependencies

Frontend: React, React DOM, React Router, Axios; Vite, React Vite plugin, Tailwind and its Vite plugin. Recharts is deferred until analytics.

Backend: FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, Psycopg binary, python-multipart, pwdlib with Argon2, PyJWT, Alembic; opencv-python-headless, numpy, pillow; paddleocr, paddlepaddle; pytest and HTTPX for tests.

Deferred dependencies: PDF library in Phase 11. No legal compliance evaluation or rule verdicts are included in Phase 5.

## Phase 5 Verification

1. Run `pytest` in `backend/` (100 passed).
2. Run `npm.cmd run build` in `frontend/` (0 errors).
3. Run `alembic upgrade head` (Revisions `0001_users`, `0002_inspections`, `0003_image_quality`, `0004_ocr`).
4. Execute live API verification suite testing OCR text recognition, polygon bounding boxes, reading order, confidence tiers, batch OCR, multi-panel summary, RBAC, and IDOR protection.
5. Live smoke test running real PaddleOCR 3.7.0 deep learning inference on CPU (`test_paddle_ocr_real.py`).

## Phase 6 delivery boundary

Deterministic extraction only. No LLM dependency, legal verdicts, applicability logic, rule execution, manual compliance overrides, or reports. See PHASE6_COMPLETION.md for the completion report and VERIFICATION.md for reproducible checks.

## Phase 7 delivery boundary

Context preparation is complete. Applicability hints remain unverified and non-executable. No legal verdicts, rule execution, reports, finalization, or sector-specific evaluation. See PHASE7_COMPLETION.md. Wait for **Continue to Phase 8.**
