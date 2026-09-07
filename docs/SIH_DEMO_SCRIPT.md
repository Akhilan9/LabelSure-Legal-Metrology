# LabelSure · SIH 2026 Grand Finale Demonstration Script
**Problem Statement SIH26034 · Team APEX**  
*Automated Verification of Statutory Declarations on Packaged Commodities under the Legal Metrology Act, 2009 & Packaged Commodities Rules (PCR), 2011.*

---

## 🏛️ System Philosophy

$$\Large \mathbf{\text{AI OBSERVES. RULES DECIDE. EVIDENCE EXPLAINS. INSPECTORS VERIFY.}}$$

| Principle | Technical Implementation |
| :--- | :--- |
| **1. AI Observes** | OpenCV CLAHE + Bilateral Preprocessing & PaddleOCR / Tesseract extract raw visual candidate tokens and spatial polygons. |
| **2. Rules Decide** | Deterministic Abstract Syntax Tree (AST) engine evaluates statutory rules over frozen canonical snapshots (`RuleInputSnapshot`). **Zero LLM hallucination in legal decisions.** |
| **3. Evidence Explains** | **RuleLens** provides full provenance: Statutory Rule $\to$ Evaluated Fact $\to$ Candidate Declaration $\to$ OCR Block $\to$ Exact Image Bounding Box. |
| **4. Inspectors Verify** | Human review decisions and verdict overrides are recorded with mandatory justifications and immutable audit logs (`audit_events`). |

---

## 🚀 1-Click Launch & Credentials

### Launching the Platform
Double-click `Start-LabelSure.bat` in the repository root (or run `./Start-LabelSure.bat` in terminal).  
The launcher automatically:
1. Validates Python 3.11+ and Node.js environments.
2. Applies all database schema migrations (`alembic upgrade head`).
3. Seeds standard role users and 5 judge-ready test scenarios (`seed_demo_scenarios.py`).
4. Launches FastAPI backend (`http://localhost:8000`) and Vite frontend (`http://localhost:5173`).
5. Opens `http://localhost:5173` directly in your browser.

### User Role Credentials Matrix
| Role | Email | Default Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@labelsure.local` | `TestPassword123!` | System settings, user management, full audit trail, finalize & reopen reviews |
| **Supervisor** | `supervisor@labelsure.local` | `TestPassword123!` | Enforcement analytics, cross-inspector queue, finalize & approve inspections |
| **Inspector** | `inspector@labelsure.local` | `TestPassword123!` | Inspection creation, evidence capture, candidate verification, review & export |

*(Note: If initialized via custom environment variables, fallback password `AdminPassword123!` / `SupervisorPassword123!` / `InspectorPassword123!` is also accepted).*

---

## 📋 Pre-Seeded Judge Scenarios Reference

| Code | Commodity Name | Category & Type | Automated Verdict | Key Demonstration Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`INS-2026-DEMO01`** | **Amul Gold Milk (500 ml)** | Food Pouch (Domestic) | **`COMPLIANT` (`PASS`)** | Full statutory compliance across all declarations (MRP, Net Qty, Date, Customer Care). |
| **`INS-2026-DEMO02`** | **Crispy Crunch Potato Chips** | Food Pouch (Domestic) | **`NON_COMPLIANT` (`FAIL`)** | Clear violation detection: Missing mandatory Consumer Care contact & missing Packing Date. |
| **`INS-2026-DEMO03`** | **Pure Forest Organic Honey** | Food Jar (Domestic) | **`UNCERTAIN`** | Image quality defense: Low-light blurry capture triggers safe uncertain state instead of false violation. |
| **`INS-2026-DEMO04`** | **Swiss Deluxe Chocolate 85%** | Food Box (Imported) | **`COMPLIANT` (`PASS`)** | Specific statutory import rules: Country of Origin and Importer Name & Address validation. |
| **`INS-2026-DEMO05`** | **NutriDelight Rolled Oats** | Food Box (Domestic) | **`COMPLIANT` (`OVERRIDDEN`)** | Full Human-in-the-Loop workflow: Inspector physically verifies faint embossed MRP and overrides verdict with audit log. |

---

## 🎭 Step-by-Step 5-Act Demonstration Guide

### Act 1: Enforcement Command Center & Review Queue (2 mins)
1. **Login** as Supervisor: `supervisor@labelsure.local` / `SupervisorPassword123!`.
2. **Examine Operational KPIs**:
   - Total Inspections, Active Drafts, Evidence Processed, and Ready for Pipeline Analysis.
   - Compliance Rate progress bars segmented across commodity categories (Food, Electronics, Cosmetics, FMCG).
   - Violation Hotspot chart showing top statutory failure causes (Missing Consumer Care, Invalid Units, Missing Date).
3. **Explore Prioritized Review Queue**:
   - Highlight the **Algorithmic Urgency Scoring**:
     $$\text{Urgency Score} = (\text{Violations} \times 30) + (\text{Uncertain} \times 15) + (\text{Overrides} \times 10) + \min(20, \text{Days Pending} \times 2)$$
   - Point out how non-compliant and low-confidence inspections automatically bubble up to `CRITICAL` and `HIGH` priority badges.

---

### Act 2: Evidence Ingestion & Computer Vision Quality Gate (2 mins)
1. Navigate to **Create Inspection** (`/inspections/new`).
2. Input Commodity Metadata:
   - Product Name: `Himalayan Mineral Spring Water 1L`
   - Category: `FOOD`, Package Type: `BOTTLE`, Import Status: `DOMESTIC`
3. Upload Package Image and observe the **Computer Vision Preprocessing Pipeline**:
   - **EXIF Auto-Orientation**: Transposes camera orientation tags safely.
   - **Decompression Bomb Protection**: Hardened against pixel-bomb denial of service (`MAX_IMAGE_PIXELS = 50M`).
   - **CLAHE Contrast Normalization**: Enhances low-contrast label text in LAB color space.
   - **Bilateral Noise Filtering**: Removes sensor noise while preserving sharp font edges.
   - **Quality Assessment Gate**: Real-time evaluation of Blur Laplacian variance, Luminance, and Glare.

---

### Act 3: Deterministic Rule Engine & RuleLens Explainability (3 mins)
1. Open inspection **`INS-2026-DEMO02`** (Crispy Crunch Potato Chips).
2. Click **Execute Rule Evaluation** (or inspect pre-evaluated results).
3. Showcase the **4-Valued Verdict Space**:
   - `PASS`: Requirement satisfied by unambiguous evidence.
   - `FAIL`: Requirement violated with high-confidence evidence.
   - `UNCERTAIN`: Evidence quality is insufficient to legally prove presence or absence.
   - `NOT_APPLICABLE`: Rule not relevant to this commodity category/import type.
4. Open the **RuleLens Explainability Modal** on Rule `Rule 6(1)(h) - Consumer Care Details`:
   - **Statutory Citation**: Direct quote of Legal Metrology (Packaged Commodities) Rules 2011.
   - **AST Decision Steps**: Step-by-step logic breakdown showing why the rule failed.
   - **Counterfactual Guidance**: Plain-English instructions detailing how the manufacturer can achieve compliance.
   - **Interactive Visual Provenance**: Click on extracted candidates to highlight exact spatial polygon coordinates on the package image.

---

### Act 4: Human-in-the-Loop Overrides & Immutable Audit Trail (3 mins)
1. Open inspection **`INS-2026-DEMO05`** (NutriDelight Rolled Oats).
2. Demonstrate **Strict Machine vs Human Separation**:
   - Machine observation: Automated OCR returned `UNCERTAIN` due to faint embossed print.
   - Inspector action: Field inspector conducted physical magnifying loupe inspection.
3. Perform a **Verdict Override**:
   - Click **Override Verdict** on `MRP_PRESENCE`.
   - Change verdict from `UNCERTAIN` to `PASS`.
   - Enter Mandatory Justification: *"Embossed price stamp verified on top flap under 10x optical magnification: MRP Rs. 195.00 incl. of all taxes."*
   - Save decision.
4. Inspect the **Immutable Audit Trail**:
   - Scroll to **Audit Trail Ledger**.
   - Show the immutable chronological log recording: Inspector Name, Timestamp, Action (`OVERRODE_RULE_VERDICT`), Before State, After State, and Justification.
5. Click **Finalize Inspection**:
   - Locks the inspection record into immutable `FINALIZED` state.
   - Notice that non-admin users cannot alter or tamper with finalized records.

---

### Act 5: Regulatory Compliance Reports & Cryptographic Verification (2 mins)
1. Navigate to **Inspection Reports** (`INS-2026-DEMO01` or `INS-2026-DEMO05`).
2. Click **Download Regulatory PDF Report**:
   - Open the generated PDF in the browser.
   - Highlight the **ReportLab Two-Pass Layout**:
     - Official Government-format header with National Emblem seal placeholder.
     - Inspection metadata summary table.
     - Color-coded Compliance Status Banner (`COMPLIANT` / `NON-COMPLIANT`).
     - Complete Statutory Rule Ledger with legal references.
     - Human review & override addendum.
     - Running headers, "Page X of Y" dynamic footers, and official background watermark.
     - **Cryptographic SHA-256 Tamper-Evident Checksum** printed at the document base.
3. Click **Export CSV Ledgers**:
   - Download the Statutory Violations CSV and Declarations CSV.
   - Explain the **Spreadsheet Formula Injection Defense**: All cells starting with `=`, `+`, `-`, `@`, `\t` are automatically sanitized with a leading apostrophe (`'`) to prevent CSV injection attacks.
4. Click **View Canonical JSON Snapshot**:
   - Show the deterministic snapshot JSON and one-click copy of the SHA-256 verification hash for external regulatory archival.

---

## 🏆 Key Architectural Highlights for Judges

| Evaluation Dimension | LabelSure Implementation |
| :--- | :--- |
| **Legal Robustness** | Strict mapping to Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011. Zero LLM hallucinations in statutory decisions. |
| **Explainability** | Full multi-tier provenance chain tracing every statutory decision down to image pixel coordinates. |
| **Security & Integrity** | Cross-inspector IDOR authorization, image decompression bomb protection, security HTTP headers, formula injection defense, cryptographic SHA-256 report verification. |
| **Human Accountability** | Clear separation between machine observations and human officer decisions with mandatory override rationales and immutable audit trails. |
| **Production Readiness** | 100% test pass rate across 238 automated tests; turnkey single-click launcher with pre-seeded realistic scenarios. |
