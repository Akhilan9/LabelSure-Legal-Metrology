

**Current release: Phase 7 — Product/Package Context and Applicability Preparation.**

Phase 6 adds deterministic, evidence-linked declaration candidates on top of the Phase 5 OCR foundation.
Retains Phase 0-4 foundations (React/Vite frontend, FastAPI backend, SQLAlchemy ORM, Alembic migrations, JWT authentication, Argon2 hashing, RBAC, inspection lifecycle, multi-image evidence ingestion, binary magic bytes validation, SHA-256 integrity, local storage abstraction, image quality assessment, and OpenCV preprocessing). Adds OCR provider abstraction with CPU-compatible deep-learning engine **PaddleOCR 3.7.0 (PP-OCRv6)** and deterministic **MockOCRProvider**, traceable database models (`OCRRun`, `OCRBlock`), Alembic migration `0004_ocr`, text normalization and reading order spatial sorting, confidence tier categorization (`GOOD`, `REVIEW`, `LOW`), single/batch OCR execution endpoints, multi-panel OCR summary aggregation, and interactive frontend bounding box visualizer canvas with reading order and confidence tier overlays.

## Quick Start with One Double-Click

### Flutter Multiplatform Frontend (Recommended)
Double-click **Start-LabelSure-Flutter.bat** in the project folder. It verifies the Flutter SDK, sets up the Python backend venv, applies Alembic migrations, starts the FastAPI backend on port 8000, and launches the complete Flutter web application on port 5173 (`http://localhost:5173`).

### React / Vite Frontend
Double-click **Start-LabelSure.bat** to start the React/Vite edition on `http://localhost:5173`.

## Run Flutter Locally — Windows PowerShell

Prerequisites: Flutter 3.24+ (Dart 3.5+), Python 3.11+.

Backend, terminal 1:
```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m app.scripts.configure_local
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.scripts.seed_users
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Flutter App, terminal 2:
```powershell
Set-Location frontend_flutter
flutter pub get
flutter run -d chrome --web-port 5173
# Or run Windows desktop app:
# flutter run -d windows
```

Open `http://localhost:5173`. API Swagger docs: `http://127.0.0.1:8000/docs`.

Flutter Verification & Analysis:
```powershell
Set-Location frontend_flutter
flutter analyze
flutter build web --release
```

## Run React Locally — Windows PowerShell

Prerequisites: Python 3.13, Node.js 22.12+.

Backend, terminal 1:
```powershell
Set-Location E:\APEX\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m app.scripts.configure_local
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.scripts.seed_users
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, terminal 2:
```powershell
Set-Location E:\APEX\frontend
npm.cmd ci
Copy-Item .env.example .env
npm.cmd run dev
```

Open `http://localhost:5173`. API Swagger docs: `http://127.0.0.1:8000/docs`.

Verification, terminal 3:
```powershell
Set-Location E:\APEX\backend
.\.venv\Scripts\python.exe -m pytest -v
Set-Location E:\APEX\frontend
npm.cmd run build
```

## Phase 5 Features

- **OCR Provider Abstraction**: `BaseOCRProvider` interface supporting production engine **PaddleOCR 3.7.0** (CPU inference with PP-OCRv6) and deterministic **MockOCRProvider** for zero-latency test automation.
- **Traceable OCR Data Architecture**: 
  - `OCRRun`: Records engine metadata, versions, language, status (`SUCCESS`, `PARTIAL`, `FAILED`), execution duration, average confidence, block counts, and error tracking.
  - `OCRBlock`: Stores `raw_text` (immutable legal evidence), `normalized_text` (NFKC, whitespace normalization), `confidence` (0.0-1.0), `confidence_tier` (`GOOD` >= 0.85, `REVIEW` >= 0.60, `LOW` < 0.60), 4-point polygon coordinates, axis-aligned bounding box, `line_number`, and `reading_order`.
- **Statutory Text Normalization & Reading Order**: Cleans whitespace and exotic characters while preserving statutory numbers, symbols (₹, Rs.), units (g, ml, kg), and dates. Clusters lines by vertical proximity and orders top-to-bottom, left-to-right.
- **Evidence Immutability & Traceability**: Runs OCR directly on Phase 4 derived OCR-ready preprocessed artifacts (`storage/inspections/<id>/processed/<image_id>/ocr_ready.png`) while keeping original raw evidence untouched.
- **Single & Batch OCR Endpoints**:
  - `POST /api/v1/inspections/{id}/images/{image_id}/ocr`: Single image OCR execution with versioned idempotency caching (`ocr_version="1"`).
  - `POST /api/v1/inspections/{id}/ocr`: Batch OCR processing all evidence panels of an inspection.
  - `GET /api/v1/inspections/{id}/images/{image_id}/ocr`: Fetch latest image OCR run and extracted text blocks.
  - `GET /api/v1/inspections/{id}/images/{image_id}/ocr/blocks`: List raw OCR blocks for an image.
  - `GET /api/v1/inspections/{id}/ocr/summary`: Aggregate multi-panel OCR text summary across all package sides.
- **Interactive Frontend OCR UI**:
  - Interactive SVG bounding box visualizer with confidence tier color coding (`GOOD` emerald, `REVIEW` amber, `LOW` rose), reading order badges, and hover/click block inspection.
  - Structured text block table with search, tier filtering, and clipboard copy.
  - Multi-panel inspection OCR text summary tab with copy-all capability.
- **Strict Role-Based Access Control**:
  - `INSPECTOR`: Run OCR on own inspections, view extracted text and bounding boxes.
  - `ADMIN`: Full execution and visibility across all inspections.
  - `SUPERVISOR`: Read-only access to OCR runs, blocks, bounding boxes, and multi-panel summaries. Cannot trigger OCR mutations.

## Phase 6 — Structured Declaration Extraction

From an inspection, run OCR, then select **Extract declarations** in **Extracted Declarations**. Candidates show values, confidence, panel/image, method, and review reasons. **View evidence** displays the supporting OCR blocks and bounding boxes. Conflicting strong values remain visible and require review.

The deterministic extractor supports product names; manufacturer/packer/importer names and addresses; quantity; MRP; month/year; origin; consumer-care name/address/phone/email; validated contextual GTIN; unit sale price; and explicitly labeled other declarations. No LLM service or API key is required.

Set `EXTRACTION_PIPELINE_VERSION=1` in backend configuration (default 1). Run `alembic upgrade head` to apply `0005_extraction`. New OCR/context/version snapshots invalidate the current extraction view; historical candidate evidence remains linked.

Extracted declarations are machine-generated candidates. Extraction does not establish legal compliance. OCR errors may propagate; low confidence needs review; missing candidates do not prove absence. Company/address and product-name parsing are heuristic. No Legal Metrology rule engine is implemented.

See [architecture](docs/ARCHITECTURE.md), [API contract](docs/API_CONTRACT.md), [verification](docs/VERIFICATION.md), and [Phase 6 completion report](docs/PHASE6_COMPLETION.md). Phase 6 is complete; Phase 7 builds on its candidate evidence.


## Phase 7 — Product/Package Context and Applicability Preparation

In Inspection Detail, open **Context & Applicability** and select **Resolve context**. Optional inspector inputs are stored separately from original inspection metadata. The section shows normalized product/package context, source facts, uncertainty/conflicts, evidence sufficiency, and applicability preparation. ADMIN can inspect the frozen rule-input JSON.

Context can begin before extraction; missing evidence stays explicit. After OCR/extraction or metadata changes, resolve again to create a fresh versioned snapshot. Historical snapshots remain unchanged. Set `CONTEXT_PIPELINE_VERSION=1` (default) and apply `alembic upgrade head` for `0006_context`.

No legal rules run in Phase 7. Preview identifiers are unverified preparation hints, not statutory conclusions. OCR errors can affect inferred context; missing candidates do not prove missing declarations. Sector-specific laws and physical font-size compliance are not evaluated.

See [Phase 7 completion report](docs/PHASE7_COMPLETION.md). Stop here; Phase 8 requires **Continue to Phase 8.**

