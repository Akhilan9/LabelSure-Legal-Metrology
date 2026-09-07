# API contract

Base path: `/api/v1`. JSON uses snake_case and UTC ISO-8601 timestamps. User IDs and Inspection IDs are UUID strings. Live schema: `http://127.0.0.1:8000/docs` and `/openapi.json`.

## Implemented Endpoints

### 1. Health & Readiness (Phase 1)
`GET /api/v1/health` — public readiness, HTTP 200:
```json
{"status":"ok","service":"labelsure-api","version":"0.4.0","database":"connected","phase":4}
```

### 2. Authentication (Phase 2)
- `POST /api/v1/auth/login` — JSON `{"email":"inspector@labelsure.local","password":"..."}` → `{"access_token": "...", "token_type": "bearer", "expires_in": 1800, "user": {...}}`
- `GET /api/v1/auth/me` — Requires `Authorization: Bearer <token>` → Returns current User object.

### 3. Inspections & Product Context (Phase 3)
- `POST /api/v1/inspections` (Roles: `ADMIN`, `INSPECTOR`):
  - Request body (all context fields optional):
    ```json
    {
      "product_name": "Almond Snack Pack",
      "brand_name": "NutriSure",
      "category": "Food & Beverages",
      "package_type": "Pouch",
      "import_status": "DOMESTIC",
      "barcode": "8901234567890",
      "manufacturer_name": "Agro Foods Ltd",
      "packer_name": null,
      "importer_name": null,
      "notes": "Sample drawn at regional warehouse"
    }
    ```
  - Response 201 Created: `InspectionResponse`

- `GET /api/v1/inspections` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Query params: `status` (DRAFT, EVIDENCE_UPLOADED, READY_FOR_ANALYSIS), `q` (search term), `page` (int >= 1), `page_size` (int 1-100).
  - Scope: `INSPECTOR` sees own created/assigned inspections; `ADMIN` and `SUPERVISOR` see all.

- `GET /api/v1/inspections/{inspection_id}` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Returns complete `InspectionResponse` with nested evidence images and attached `processing_result` objects.
  - Non-owner inspector receives 404 Not Found (IDOR defense).

- `PATCH /api/v1/inspections/{inspection_id}` (Roles: `ADMIN`, `INSPECTOR`):
  - Updates mutable metadata fields (`product_name`, `brand_name`, `category`, `notes`, etc.).
  - Rejection: 409 Conflict if inspection is in `READY_FOR_ANALYSIS` status.
  - Rejection: 403 Forbidden for `SUPERVISOR` or non-owner inspector.

- `POST /api/v1/inspections/{inspection_id}/images` (Roles: `ADMIN`, `INSPECTOR`):
  - Multipart form data: `files` (list of UploadFile), `panel_types` (list of strings).
  - Validation: Magic byte inspection (JPEG, PNG, WebP), non-zero byte check, file size limit (`MAX_UPLOAD_SIZE_MB`), total images count limit (`MAX_IMAGES_PER_INSPECTION`).
  - Status transition: Transitions `DRAFT` → `EVIDENCE_UPLOADED`.

- `GET /api/v1/inspections/{inspection_id}/images` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Returns list of `InspectionImageResponse` metadata.

- `GET /api/v1/inspections/{inspection_id}/images/{image_id}/content` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Streams immutable raw evidence image bytes with MIME type header.

- `PATCH /api/v1/inspections/{inspection_id}/images/{image_id}` (Roles: `ADMIN`, `INSPECTOR`):
  - Updates `panel_type` or `upload_order`.

- `DELETE /api/v1/inspections/{inspection_id}/images/{image_id}` (Roles: `ADMIN`, `INSPECTOR`):
  - Deletes physical storage file, derived artifact, and database record.

- `POST /api/v1/inspections/{inspection_id}/submit` (Roles: `ADMIN`, `INSPECTOR`):
  - Validates inspection has >= 1 uploaded evidence image.
  - Transitions `status = READY_FOR_ANALYSIS`, sets `submitted_at = UTC NOW`, and locks further edits.

### 4. Image Quality Assessment & OpenCV Preprocessing (Phase 4)
- `POST /api/v1/inspections/{inspection_id}/images/{image_id}/process` (Roles: `ADMIN`, `INSPECTOR`):
  - Query params: `force` (bool, default `false`).
  - Executes Laplacian focus check, mean luminance, contrast std dev, glare overexposure calculation, LAB CLAHE equalization, bilateral filtering, and lossless PNG generation.
  - Response 200 OK:
    ```json
    {
      "id": "e5c12345-832d-451e-b838-bb41a774900a",
      "inspection_image_id": "c1f72922-832d-451e-b838-bb41a774900a",
      "quality_status": "GOOD",
      "width": 1920,
      "height": 1080,
      "channels": 3,
      "metrics": {
        "blur_score": 342.5,
        "brightness_score": 142.1,
        "contrast_score": 58.4,
        "glare_score": 0.012
      },
      "flags": [],
      "processing_version": "1",
      "derived_image_available": true,
      "derived_content_url": "/api/v1/inspections/{inspection_id}/images/{image_id}/processed",
      "derived_sha256": "4a7d...64chars",
      "error_message": null,
      "processed_at": "2026-09-07T12:00:00Z"
    }
    ```

- `POST /api/v1/inspections/{inspection_id}/process-images` (Roles: `ADMIN`, `INSPECTOR`):
  - Query params: `force` (bool, default `false`).
  - Batch processes all images of an inspection.
  - Response 200 OK:
    ```json
    {
      "total_processed": 3,
      "successful_count": 3,
      "failed_count": 0,
      "results": [ ... ]
    }
    ```

- `GET /api/v1/inspections/{inspection_id}/images/{image_id}/quality` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Returns `ImageQualityResponse` metadata. Returns 404 if not yet processed.

- `GET /api/v1/inspections/{inspection_id}/images/{image_id}/processed` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Streams preprocessed OCR-ready PNG image with `Content-Type: image/png` and `Cache-Control: private, max-age=3600`.

### 5. OCR Engine & Evidence Text Extraction (Phase 5)
- `POST /api/v1/inspections/{inspection_id}/images/{image_id}/ocr` (Roles: `ADMIN`, `INSPECTOR`):
  - Query params: `force` (bool, default `false`).
  - Executes OCR provider inference on the preprocessed image artifact, computes statutory text normalization, confidence tiering, polygon bounding boxes, and reading order.
  - Response 200 OK: `OCRRunResponse` with nested `blocks`.
    ```json
    {
      "id": "7b0a7ef2-...",
      "inspection_id": "90e68d19-...",
      "inspection_image_id": "c1f72922-...",
      "image_processing_result_id": "e5c12345-...",
      "engine_name": "PaddleOCR",
      "engine_version": "3.7.0",
      "language_config": "en",
      "status": "SUCCESS",
      "average_confidence": 0.942,
      "block_count": 5,
      "started_at": "2026-09-07T12:00:00Z",
      "completed_at": "2026-09-07T12:00:01Z",
      "ocr_version": "1",
      "error_code": null,
      "error_message_safe": null,
      "blocks": [
        {
          "id": "b1234567-...",
          "ocr_run_id": "7b0a7ef2-...",
          "inspection_id": "90e68d19-...",
          "inspection_image_id": "c1f72922-...",
          "block_index": 0,
          "raw_text": "Net Quantity: 500 g",
          "normalized_text": "Net Quantity: 500 g",
          "confidence": 0.985,
          "confidence_tier": "GOOD",
          "polygon": [[20.0, 30.0], [180.0, 30.0], [180.0, 60.0], [20.0, 60.0]],
          "bounding_box": {
            "x_min": 20.0,
            "y_min": 30.0,
            "x_max": 180.0,
            "y_max": 60.0,
            "width": 160.0,
            "height": 30.0
          },
          "line_number": 1,
          "reading_order": 0,
          "created_at": "2026-09-07T12:00:01Z"
        }
      ]
    }
    ```

- `POST /api/v1/inspections/{inspection_id}/ocr` (Roles: `ADMIN`, `INSPECTOR`):
  - Query params: `force` (bool, default `false`).
  - Batch executes OCR text recognition across all evidence images of the inspection.
  - Response 200 OK: `BatchOCRResponse`
    ```json
    {
      "inspection_id": "90e68d19-...",
      "total_images": 3,
      "success": 3,
      "partial": 0,
      "failed": 0,
      "results": [ ... ]
    }
    ```

- `GET /api/v1/inspections/{inspection_id}/images/{image_id}/ocr` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Retrieves latest `OCRRunResponse` with nested blocks for an evidence image. Returns 404 if not yet processed.

- `GET /api/v1/inspections/{inspection_id}/images/{image_id}/ocr/blocks` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Retrieves list of `OCRBlockResponse` objects in reading order for an evidence image.

- `GET /api/v1/inspections/{inspection_id}/ocr/summary` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Returns aggregate multi-panel OCR text summary across all package sides.
  - Response 200 OK: `InspectionOCRSummary`
    ```json
    {
      "inspection_id": "90e68d19-...",
      "inspection_code": "INS-2026-000001",
      "total_images": 3,
      "images_processed": 3,
      "ocr_completed_count": 3,
      "ocr_failed_count": 0,
      "total_ocr_blocks": 24,
      "average_confidence": 0.935,
      "panels": [
        {
          "panel_type": "FRONT",
          "image_id": "c1f72922-...",
          "ocr_run_id": "7b0a7ef2-...",
          "status": "SUCCESS",
          "block_count": 8,
          "average_confidence": 0.945,
          "text_lines": ["LABELSURE NUTRITION", "Net Quantity: 500 g"]
        }
      ]
    }
    ```

### 6. Dashboard Summary (Phase 3-5)
- `GET /api/v1/dashboard/summary` (Roles: `ADMIN`, `INSPECTOR`, `SUPERVISOR`):
  - Returns real count metrics scoped to the caller's role.

## Planned Endpoints (Phase 7+)
- `GET /api/v1/inspections/{id}/findings` — RuleLens findings and compliance verdicts.
- `POST /api/v1/findings/{id}/review` — Inspector review and override log.
- `POST /api/v1/inspections/{id}/reports` — Generate exportable inspection reports (PDF/JSON).

## Phase 6 — declaration extraction

All endpoints require Bearer authentication. INSPECTOR access is limited to inspections they created (assignment alone does not grant Phase 6 access). ADMIN may run/read all; SUPERVISOR may only read. Unauthorized object IDs return 404; authenticated supervisor mutation returns 403; missing/invalid authentication returns 401.

| Method | Path after /api/v1 | Result |
|---|---|---|
| POST | /inspections/{inspection_id}/extract-declarations | 200 ExtractionRun; no body required; versioned, evidence-aware idempotency |
| GET | /inspections/{inspection_id}/declarations | Current candidate array; offset ≥0, limit 1–1000 (default 100) |
| GET | /inspections/{inspection_id}/declarations/{candidate_id} | Candidate with ordered OCR sources; supports authorized historical detail |
| GET | /inspections/{inspection_id}/extraction-summary | Current run or null, candidate_count, needs_review_count, conflicting_types, explanatory message |

POST returns 409 if no latest usable OCR exists and 422 if extraction limits are exceeded. No metadata-only candidates are fabricated. A successful empty result means no supported patterns were detected, not that a required declaration is absent.

Run response: id, inspection_id, version, status, started_at, completed_at, candidate_count, error_code, warnings. Missing/partial/failed panels produce PARTIAL when other usable evidence exists.

Candidate response: id, extraction_run_id, inspection_id, declaration_type, raw_value, normalized_value, structured_value, source_ocr_run_id, source_ocr_block_id, source_image_id, source_image_variant, panel_type, confidence_score, confidence_factors, extraction_method, is_primary, needs_review, review_status, review_reasons, created_at, updated_at, sources.

Each source has ocr_block_id, sequence_order, raw_text, polygon, bounding_box. Candidate evidence uses the existing authorized image content/processed endpoints. No raw storage path is exposed.

Structured examples: MRP {"amount":"120.00","currency":"INR"}; NET_QUANTITY {"numeric_value":"500","unit":"g"}; MONTH_YEAR {"month":8,"year":2026}. Internal image-variant metadata may also appear. Ambiguous "08-26" retains year=null and year_text="26". No legal conclusion is returned.

Review status vocabulary: AUTO_EXTRACTED, NEEDS_REVIEW, VERIFIED, REJECTED. Phase 6 creates only the first two; no verification/rejection endpoint is provided.


## Phase 7 — Context & Applicability

All endpoints require Bearer authentication and inspection ownership checks. INSPECTOR may resolve/read only inspections they created; ADMIN may resolve/read all; SUPERVISOR is read-only. Assignment alone does not grant Phase 7 access.

| Method | Path after /api/v1 | Behavior |
|---|---|---|
| POST | /inspections/{inspection_id}/resolve-context | Resolve metadata/evidence and optional explicit inspector input |
| GET | /inspections/{inspection_id}/context | Current run and resolved context; run=null if missing/stale |
| GET | /inspections/{inspection_id}/context/facts | Current snapshot's source facts; empty before resolution |
| GET | /inspections/{inspection_id}/rule-input | Current frozen snapshot; optional snapshot_id reads authorized history |
| GET | /inspections/{inspection_id}/applicability-preview | Current snapshot's non-executable preparation hints |

POST accepts no body or:
```json
{"inspector_input":{"product_category":"Food","package_type":"POUCH","import_status":"DOMESTIC","country_of_origin":"India","quantity_kind":"WEIGHT"}}
```
Each field is optional. Omission retains saved explicit input; null removes it. Category/origin strings are bounded to 100 characters. Package/import/quantity fields use controlled enum values. Unknown extra keys, arbitrary internal rule keys, invalid enums, and oversized/control-character input return 422.

Resolution can run before OCR/extraction. Missing extraction yields null/UNKNOWN detection facts, with evidence limitations. A completed extraction with no matching candidate yields false detection, never a legal absence finding.

Context response includes run metadata/counts, inspection_id, resolved (value/state/source_type/confidence/fact_ids), resolution_status, evidence, conflicts, and saved inspector_input. Run statuses persist SUCCESS or PARTIAL for completed calls; unexpected errors roll back atomically.

Rule-input response includes id, content_sha256, created_at, and immutable content. Content schema version 1 contains inspection_id, context_version, context_run_id, input_fingerprint, resolved, context_keys, evidence, conflicts, facts, declarations, source_inputs, applicability_preview, and limitations. Keys carry resolution state and provenance rather than bare authoritative values.

Preview items include rule_key, state, reason, verification_status=TODO_LEGAL_VERIFICATION, executable=false. States are POTENTIALLY_APPLICABLE, NOT_APPLICABLE_BY_CONTEXT, or APPLICABILITY_UNCERTAIN. These are not legal verdicts.

401: missing/invalid auth. 403: supervisor resolution. 404: inaccessible inspection/snapshot or unavailable current snapshot. 409: snapshot integrity mismatch. 422: invalid input or snapshot-size limit. No PATCH/PUT/DELETE snapshot API is exposed. Full rule-input API is authorized for all viewing roles; the optional raw JSON UI is ADMIN-only.

