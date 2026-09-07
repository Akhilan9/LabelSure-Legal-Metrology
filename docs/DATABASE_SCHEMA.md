# Database schema design

Phase 2 implemented `users` via revision `0001_users`.
Phase 3 implemented `inspections` and `inspection_images` via revision `0002_inspections`.
Phase 4 implements `image_processing_results` via revision `0003_image_quality`.
Phase 5 implements `ocr_runs` and `ocr_blocks` via revision `0004_ocr`.

Run `alembic upgrade head` to apply all migrations.

## Implemented Tables

### 1. `users` (Alembic `0001_users`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `full_name` | VARCHAR(150) | No | Officer / User display name |
| `email` | VARCHAR(254) | No | Unique index, normalized lowercase |
| `hashed_password` | VARCHAR(255) | No | Argon2id hash |
| `role` | VARCHAR(20) | No | CHECK (`role IN ('ADMIN', 'INSPECTOR', 'SUPERVISOR')`) |
| `is_active` | BOOLEAN | No | Account status flag |
| `created_at` | TIMESTAMP (TZ) | No | UTC creation timestamp |
| `updated_at` | TIMESTAMP (TZ) | No | UTC last update timestamp |

### 2. `inspections` (Alembic `0002_inspections`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `inspection_code` | VARCHAR(32) | No | Unique index, human-readable e.g. `INS-2026-000001` |
| `created_by_user_id` | VARCHAR(36) | No | FK → `users.id`, index |
| `assigned_to_user_id` | VARCHAR(36) | Yes | FK → `users.id`, index |
| `status` | VARCHAR(30) | No | `DRAFT`, `EVIDENCE_UPLOADED`, `READY_FOR_ANALYSIS`, etc. |
| `product_name` | VARCHAR(255) | Yes | Product name under inspection |
| `brand_name` | VARCHAR(255) | Yes | Brand name |
| `category` | VARCHAR(100) | Yes | Product category (Food, Cosmetic, etc.) |
| `package_type` | VARCHAR(100) | Yes | Package type (Pouch, Box, Bottle, etc.) |
| `import_status` | VARCHAR(20) | Yes | `UNKNOWN`, `DOMESTIC`, `IMPORTED` |
| `barcode` | VARCHAR(64) | Yes | Barcode / GTIN / EAN, index |
| `manufacturer_name` | VARCHAR(255) | Yes | Declared manufacturer name |
| `packer_name` | VARCHAR(255) | Yes | Declared packer name |
| `importer_name` | VARCHAR(255) | Yes | Declared importer name |
| `notes` | TEXT | Yes | Field inspector remarks |
| `created_at` | TIMESTAMP (TZ) | No | UTC creation timestamp, index |
| `updated_at` | TIMESTAMP (TZ) | No | UTC update timestamp |
| `submitted_at` | TIMESTAMP (TZ) | Yes | Timestamp of final submission |

### 3. `inspection_images` (Alembic `0002_inspections`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `inspection_id` | VARCHAR(36) | No | FK → `inspections.id` (ON DELETE CASCADE), index |
| `uploaded_by_user_id` | VARCHAR(36) | No | FK → `users.id` (ON DELETE RESTRICT), index |
| `original_filename` | VARCHAR(255) | No | User-provided client filename |
| `stored_filename` | VARCHAR(255) | No | Cryptographic safe filename on disk |
| `storage_path` | VARCHAR(512) | No | Relative safe path inside storage directory |
| `mime_type` | VARCHAR(64) | No | `image/jpeg`, `image/png`, `image/webp` |
| `file_size` | INTEGER | No | Byte count |
| `sha256` | VARCHAR(64) | No | SHA-256 cryptographic digest of raw bytes |
| `panel_type` | VARCHAR(32) | No | `FRONT`, `BACK`, `LEFT`, `RIGHT`, `TOP`, `BOTTOM`, `DECLARATION_PANEL`, `MRP_PANEL`, `OTHER` |
| `upload_order` | INTEGER | No | Sequence order of upload |
| `width` | INTEGER | Yes | Image width in pixels |
| `height` | INTEGER | Yes | Image height in pixels |
| `quality_status` | VARCHAR(32) | Yes | Current quality status (`GOOD`, `ACCEPTABLE`, `POOR`, `UNREADABLE`, `PROCESSING_FAILED`) |
| `created_at` | TIMESTAMP (TZ) | No | UTC upload timestamp |

### 4. `image_processing_results` (Alembic `0003_image_quality`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `inspection_image_id` | VARCHAR(36) | No | FK → `inspection_images.id` (ON DELETE CASCADE), UNIQUE index |
| `width` | INTEGER | No | Pixel width of processed frame |
| `height` | INTEGER | No | Pixel height of processed frame |
| `channels` | INTEGER | Yes | Number of color channels (e.g. 3 for BGR) |
| `blur_score` | FLOAT | Yes | Variance of Laplacian edge sharpness metric |
| `brightness_score` | FLOAT | Yes | Grayscale mean luminance [0.0 - 255.0] |
| `contrast_score` | FLOAT | Yes | Grayscale standard deviation |
| `glare_score` | FLOAT | Yes | Ratio of near-white overexposed pixels [0.0 - 1.0] |
| `quality_status` | VARCHAR(32) | No | `PENDING`, `GOOD`, `ACCEPTABLE`, `POOR`, `UNREADABLE`, `PROCESSING_FAILED`, index |
| `quality_flags` | JSON | No | List of triggered flags (`BLURRY`, `TOO_DARK`, `TOO_BRIGHT`, `LOW_CONTRAST`, `LOW_RESOLUTION`, `POSSIBLE_GLARE`, `INVALID_IMAGE`, `PROCESSING_ERROR`) |
| `derived_storage_path` | VARCHAR(500) | Yes | Storage path of derived preprocessed artifact |
| `derived_filename` | VARCHAR(255) | Yes | Storage filename (default `ocr_ready.png`) |
| `derived_sha256` | VARCHAR(64) | Yes | SHA-256 hash of derived artifact |
| `processing_version` | VARCHAR(32) | No | Pipeline version string (e.g. `"1"`) for auditability |
| `error_message` | TEXT | Yes | Stack/error details if processing failed |
| `processed_at` | TIMESTAMP (TZ) | No | Timestamp of pipeline execution |
| `created_at` | TIMESTAMP (TZ) | No | Timestamp of record creation |
| `updated_at` | TIMESTAMP (TZ) | No | Timestamp of record update |

### 5. `ocr_runs` (Alembic `0004_ocr`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `inspection_id` | VARCHAR(36) | No | FK → `inspections.id` (ON DELETE CASCADE), index |
| `inspection_image_id` | VARCHAR(36) | No | FK → `inspection_images.id` (ON DELETE CASCADE), index |
| `image_processing_result_id` | VARCHAR(36) | Yes | FK → `image_processing_results.id` (ON DELETE SET NULL), index |
| `engine_name` | VARCHAR(64) | No | OCR engine name (`PaddleOCR`, `MockOCR`) |
| `engine_version` | VARCHAR(64) | No | Engine version string (e.g. `3.7.0`) |
| `language_config` | VARCHAR(32) | No | OCR language configuration (default `en`) |
| `status` | VARCHAR(32) | No | `SUCCESS`, `PARTIAL`, `FAILED`, index |
| `average_confidence` | FLOAT | Yes | Mean confidence score across extracted blocks |
| `block_count` | INTEGER | No | Total number of extracted text blocks (default 0) |
| `started_at` | TIMESTAMP (TZ) | No | Timestamp when OCR inference began |
| `completed_at` | TIMESTAMP (TZ) | Yes | Timestamp when OCR inference finished |
| `ocr_version` | VARCHAR(32) | No | Pipeline version string (e.g. `"1"`) for idempotency |
| `error_code` | VARCHAR(64) | Yes | Safe machine-readable error code |
| `error_message_safe` | TEXT | Yes | Sanitized human-readable error description |
| `created_at` | TIMESTAMP (TZ) | No | Timestamp of record creation, index |

### 6. `ocr_blocks` (Alembic `0004_ocr`)
| Column | Type | Nullable | Constraints & Description |
|---|---|---|---|
| `id` | VARCHAR(36) | No | Primary key (UUID string) |
| `ocr_run_id` | VARCHAR(36) | No | FK → `ocr_runs.id` (ON DELETE CASCADE), index |
| `inspection_id` | VARCHAR(36) | No | FK → `inspections.id` (ON DELETE CASCADE), index |
| `inspection_image_id` | VARCHAR(36) | No | FK → `inspection_images.id` (ON DELETE CASCADE), index |
| `block_index` | INTEGER | No | Original block index in OCR engine output |
| `raw_text` | TEXT | No | Immutable verbatim OCR recognized text |
| `normalized_text` | TEXT | No | NFKC normalized and whitespace-collapsed text |
| `confidence` | FLOAT | No | Continuous recognition confidence [0.0 - 1.0] |
| `confidence_tier` | VARCHAR(20) | No | `GOOD` (>= 0.85), `REVIEW` (>= 0.60), `LOW` (< 0.60) |
| `polygon` | JSON | No | 4-point polygon `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]` |
| `bounding_box` | JSON | No | Axis-aligned box `{"x_min", "y_min", "x_max", "y_max", "width", "height"}` |
| `line_number` | INTEGER | Yes | Estimated physical line number on packaging |
| `reading_order` | INTEGER | Yes | Top-to-bottom, left-to-right reading order index |
| `created_at` | TIMESTAMP (TZ) | No | Timestamp of record creation |

## Invariants and Lifecycle
1. Evidence immutability:
   - Original image files are written once to `storage/inspections/<id>/originals/<uuid>.<ext>` and never modified.
   - Derived artifacts are stored separately under `storage/inspections/<id>/processed/<image-id>/ocr_ready.png`.
   - OCR runs operate on derived artifacts while maintaining full relational traceability back to original evidence.
2. Pipeline idempotency:
   - Re-running processing or OCR on an image with the same pipeline version returns cached metadata without duplicate filesystem or compute overhead unless `force=true`.
3. Sequential Code Sequence:
   - `generate_inspection_code()` queries highest sequence matching current year (`INS-YYYY-XXXXXX`) to ensure zero-collision monotonic ordering.

## Phase 6 tables — migration 0005_extraction

Parent revision: 0004_ocr. Migration is additive and creates no changes to existing evidence rows.

- **extraction_runs**: UUID id; inspection_id FK; version; input_fingerprint; constrained extraction status; started_at/completed_at; candidate_count; nullable error_code; JSON warnings. Unique (inspection_id, version, input_fingerprint) prevents duplicate concurrent commits for an input snapshot.
- **declaration_candidates**: UUID id; extraction_run_id/inspection_id FKs; constrained declaration_type; raw_value/normalized_value Text; structured_value JSON; source_ocr_run_id/source_ocr_block_id/source_image_id FKs; panel snapshot; confidence_score and JSON confidence_factors; constrained extraction_method; is_primary/needs_review; constrained review_status; JSON review_reasons; created_at/updated_at.
- **declaration_candidate_sources**: composite PK (candidate_id, ocr_block_id), foreign keys to candidates/OCR blocks, sequence_order. A candidate can cite multiple source blocks.

Indexed run inspection ID and candidate extraction-run, inspection, OCR-run, and image IDs support lookup. Enum check constraints reject unknown vocabulary. Source foreign keys cascade with evidence deletion; Phase 6 does not independently delete evidence. Service construction always links blocks from the candidate's OCR run and image. There is no detached manual candidate insertion endpoint.

Fresh migration, populated Phase 5 upgrade, downgrade/re-upgrade, and Alembic metadata comparison are covered by tests. The local database was backed up before upgrade and existing row contents compared afterward.


## Phase 7 — migration 0006_context

Parent revision: 0005_extraction. Four additive tables preserve Phase 6 evidence:

- **context_resolution_runs**: id, inspection_id FK/index, version, input_fingerprint, selected_at, inspector_input JSON, constrained status, started_at/completed_at, facts_created, conflicts_detected, created_at. Unique (inspection_id, version, input_fingerprint).
- **inspection_contexts**: id, inspection_id FK/index, unique run_id FK, context_version, resolved JSON, constrained resolution_status, evidence JSON, conflicts JSON, created_at/updated_at. Each row is a resolution result, not a mutable overwrite of historical context.
- **context_facts**: id, inspection_id/run_id FK indexes, constrained fact_type/source_type/resolution_state, value JSON (normalized/raw/references), source_reference_id, nullable confidence, explanation, is_active, created_at/updated_at. IDs are deterministic within the input fingerprint. is_active means participating within this run; historical run facts remain available in their frozen snapshot.
- **rule_input_snapshots**: id, inspection_id FK/index, unique run_id FK, schema_version, content JSON, content_sha256, created_at. JSON copies preserve source evidence independently of later candidate changes. ORM updates are refused; read-time canonical digest checks detect changes.

Applicability preview is embedded in the immutable snapshot rather than duplicated in a separate table. Source reference IDs are durable provenance identifiers; frozen content remains readable if mutable upstream evidence changes. Phase 8 evaluations must retain snapshot ID/hash and rule version. These tables do not contain legal verdicts.

Migration tests cover fresh head, populated Phase 6 upgrade, no model/schema drift, downgrade to Phase 6, and re-upgrade. The local database was backed up to backend/.pytest_cache/phase6_before_context.db before upgrade; every pre-existing row was compared unchanged.

