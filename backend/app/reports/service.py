from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, Role
from app.models.inspection import Inspection
from app.models.context import RuleInputSnapshot
from app.models.rules import RuleEvaluationRun
from app.models.review import InspectionReview
from app.models.reports import GeneratedReport
from app.reports.schemas import ReportSummaryResponse, GeneratedReportResponse
from app.reports.exporter import (
    generate_rules_csv,
    generate_declarations_csv,
    canonical_json_dump,
    compute_sha256
)
from app.reports.pdf_generator import build_inspection_pdf


class ReportService:
    def __init__(self, db: Session, settings=None):
        self.db = db
        self.settings = settings

    def _get_inspection(self, inspection_id: str, user: User) -> Inspection:
        inspection = self.db.scalar(select(Inspection).where(Inspection.id == inspection_id))
        if not inspection:
            raise HTTPException(404, "Inspection not found")
        if user.role == Role.INSPECTOR and inspection.created_by_user_id != user.id:
            raise HTTPException(403, "Access restricted to the inspection owner")
        return inspection

    def build_report_data(self, inspection_id: str, user: User) -> dict:
        inspection = self._get_inspection(inspection_id, user)

        # 1. Fetch latest rule evaluation run
        latest_eval = self.db.scalar(
            select(RuleEvaluationRun)
            .where(RuleEvaluationRun.inspection_id == inspection_id)
            .order_by(RuleEvaluationRun.created_at.desc())
        )

        if not latest_eval and inspection.images:
            from app.ocr.service import OCRService
            from app.storage.service import LocalStorageService
            from app.extraction.service import ExtractionService
            from app.context.service import ContextService
            from app.rules.engine import RuleEngine
            from app.rules.schemas import EvaluateRequest
            try:
                OCRService(self.db, self.settings, LocalStorageService(self.settings.storage_local_dir)).batch_process_inspection_ocr(inspection_id, user)
                ExtractionService(self.db, self.settings).run(inspection_id, user)
                ContextService(self.db, self.settings).run(inspection_id, user)
                RuleEngine(self.db, self.settings).evaluate(inspection_id, user, EvaluateRequest())
                latest_eval = self.db.scalar(
                    select(RuleEvaluationRun)
                    .where(RuleEvaluationRun.inspection_id == inspection_id)
                    .order_by(RuleEvaluationRun.created_at.desc())
                )
            except Exception as e:
                print("Auto-run evaluation during report generation:", e)

        # 2. Fetch human review
        review = self.db.scalar(
            select(InspectionReview)
            .where(InspectionReview.inspection_id == inspection_id)
            .order_by(InspectionReview.created_at.desc())
        )

        decisions_by_key = {}
        if review:
            for d in review.rule_decisions:
                decisions_by_key[d.rule_key] = d

        # 3. Construct rule evaluations with overrides merged
        rule_evaluations = []
        pass_count = 0
        violations_count = 0
        uncertain_count = 0
        overrides_count = 0

        if latest_eval:
            for r in latest_eval.results:
                human_dec = decisions_by_key.get(r.rule_key)
                machine_verdict = r.verdict
                if human_dec:
                    final_verdict = human_dec.final_verdict
                    is_overridden = human_dec.is_overridden
                    override_reason = human_dec.override_reason
                    reviewer_notes = human_dec.reviewer_notes
                else:
                    final_verdict = machine_verdict
                    is_overridden = False
                    override_reason = None
                    reviewer_notes = None

                if is_overridden:
                    overrides_count += 1
                if final_verdict == "PASS":
                    pass_count += 1
                elif final_verdict == "FAIL":
                    violations_count += 1
                elif final_verdict == "UNCERTAIN":
                    uncertain_count += 1

                rule_evaluations.append({
                    "rule_id": r.rule_id,
                    "rule_key": r.rule_key,
                    "rule_version": r.rule_version,
                    "title": r.title,
                    "legal_reference": r.legal_reference,
                    "legal_status": r.legal_status,
                    "severity": r.severity,
                    "machine_verdict": machine_verdict,
                    "original_verdict": machine_verdict,
                    "final_verdict": final_verdict,
                    "is_overridden": is_overridden,
                    "override_reason": override_reason,
                    "reviewer_notes": reviewer_notes,
                    "reason_code": r.reason_code,
                    "explanation": r.explanation,
                    "evidence_confidence": r.evidence_confidence
                })

        # 4. Determine overall compliance
        if review and review.status == "FINALIZED" and review.final_compliance_status:
            overall_compliance = review.final_compliance_status
        elif violations_count > 0:
            overall_compliance = "NON_COMPLIANT"
        elif uncertain_count > 0:
            overall_compliance = "UNCERTAIN"
        elif pass_count > 0:
            overall_compliance = "COMPLIANT"
        else:
            overall_compliance = "UNCERTAIN"

        # 5. Declarations summary from snapshot or candidates DB
        declarations_summary = []
        if latest_eval and latest_eval.rule_input_snapshot_id:
            snapshot = self.db.scalar(select(RuleInputSnapshot).where(RuleInputSnapshot.id == latest_eval.rule_input_snapshot_id))
            if snapshot and snapshot.content:
                for d in snapshot.content.get("declarations", []):
                    declarations_summary.append({
                        "id": d.get("id"),
                        "declaration_type": d.get("declaration_type"),
                        "normalized_value": d.get("normalized_value"),
                        "raw_value": d.get("raw_value"),
                        "confidence_score": d.get("confidence_score"),
                        "extraction_method": d.get("extraction_method"),
                        "needs_review": d.get("needs_review", False),
                        "review_status": d.get("review_status", "AUTO_EXTRACTED")
                    })

        if not declarations_summary:
            from app.models.extraction import DeclarationCandidate
            candidates = self.db.scalars(
                select(DeclarationCandidate).where(DeclarationCandidate.inspection_id == inspection_id)
            ).all()
            for c in candidates:
                declarations_summary.append({
                    "id": c.id,
                    "declaration_type": c.declaration_type,
                    "normalized_value": c.normalized_value,
                    "raw_value": c.raw_value,
                    "confidence_score": c.confidence_score,
                    "extraction_method": c.extraction_method,
                    "needs_review": c.needs_review,
                    "review_status": c.review_status
                })

        # Hazard Explanations Engine for Violations & Non-Compliance
        hazard_explanations = []
        HAZARD_MAP = {
            "NET_QUANTITY": {
                "title": "Net Quantity Declaration Violations",
                "reason": "Net Quantity declaration is missing, unreadable, or not expressed in standard legal units (g, kg, ml, l, m, N, Count).",
                "hazard": "Risk of consumer short-delivery deception. Prevents consumer from verifying true weight/volume. Punishable under Section 36 of Legal Metrology Act, 2009 with fine up to ₹25,000."
            },
            "MRP": {
                "title": "Maximum Retail Price (MRP) Non-Compliance",
                "reason": "MRP declaration is missing, improperly formatted without 'incl. of all taxes', or missing Unit Sale Price (USP).",
                "hazard": "Retail overcharging and price opacity hazard. Violates mandatory consumer transparency under Rule 6(1)(e) & Section 36 of Legal Metrology Act, 2009."
            },
            "COMMON_NAME": {
                "title": "Common / Generic Commodity Name Missing",
                "reason": "Generic or common name of the commodity is absent on the principal display panel.",
                "hazard": "Product identity deception. Prevents consumers from identifying the true nature of packaged goods under Rule 6(1)(b)."
            },
            "PACKING_DATE": {
                "title": "Month & Year of Packaging / Import Missing",
                "reason": "Month and Year of Packaging or Import absent or unreadable on package panel.",
                "hazard": "Shelf-life & freshness uncertainty. Consumers cannot ascertain product age, creating food safety/quality risk under Rule 6(1)(d)."
            },
            "MANUFACTURER": {
                "title": "Manufacturer / Packer Details Omission",
                "reason": "Manufacturer or Packer name, complete postal address, or PIN code missing.",
                "hazard": "Corporate untraceability hazard. Prevents consumers and legal authorities from identifying the legally responsible entity under Rule 6(1)(a)."
            },
            "CONSUMER_CARE": {
                "title": "Consumer Care Helpline & Redressal Omission",
                "reason": "Mandatory Consumer Care phone number, email address, or grievance contact address absent.",
                "hazard": "Statutory grievance denial hazard. Deprives consumers of statutory right to register product complaints under Rule 6(1)(h)."
            },
            "ORIGIN": {
                "title": "Country of Origin Omission",
                "reason": "Country of Origin missing for imported packaged commodity.",
                "hazard": "Import origin ambiguity hazard. Violates mandatory import declaration regulations under Rule 6(1)(aa)."
            },
            "EXPIRY": {
                "title": "Best Before / Expiry Date Omission",
                "reason": "Best Before / Expiry date missing on perishable packaged commodity.",
                "hazard": "Consumer health and safety hazard. Exposes consumers to expired product consumption risks under Rule 6(1)(da)."
            }
        }
        # Alias keys for R-LMPC-RULE6-* variants
        HAZARD_MAP["R-LMPC-RULE6-NETQTY"] = HAZARD_MAP["NET_QUANTITY"]
        HAZARD_MAP["R-LMPC-RULE6-MRP"] = HAZARD_MAP["MRP"]
        HAZARD_MAP["R-LMPC-RULE6-DATE"] = HAZARD_MAP["PACKING_DATE"]
        HAZARD_MAP["R-LMPC-RULE6-MFG"] = HAZARD_MAP["MANUFACTURER"]
        HAZARD_MAP["R-LMPC-RULE6-CARE"] = HAZARD_MAP["CONSUMER_CARE"]
        HAZARD_MAP["R-LMPC-RULE6-ORIGIN"] = HAZARD_MAP["ORIGIN"]

        for r in rule_evaluations:
            if r["final_verdict"] in {"FAIL", "UNCERTAIN"}:
                k = r["rule_key"]
                info = HAZARD_MAP.get(k, {
                    "title": f"Non-Compliance in {r['title']}",
                    "reason": r.get("explanation") or "Declaration failed statutory Rule 6 verification.",
                    "hazard": "Violates mandatory Legal Metrology (Packaged Commodities) Rules, 2011. Subject to statutory enforcement notice."
                })
                hazard_explanations.append({
                    "rule_key": k,
                    "title": info["title"],
                    "verdict": r["final_verdict"],
                    "reason": info["reason"],
                    "hazard": info["hazard"]
                })

        # Global & Multi-Country Metrological Standards Comparison Matrix
        dec_types = {d.get("declaration_type") for d in declarations_summary}
        international_matrix = [
            {
                "parameter": "Maximum Retail Price (MRP)",
                "india": "COMPLIANT" if "MRP" in dec_types or "UNIT_SALE_PRICE" in dec_types else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(e): Mandatory MRP ('incl. of all taxes') & USP",
                "usa": "EXEMPT",
                "usa_note": "NIST Handbook 133 / FPLA: Price set by retailer at POS",
                "eu_uk": "EXEMPT",
                "eu_uk_note": "EU Dir 76/211/EEC: Price declared on shelf tag",
                "canada": "EXEMPT",
                "canada_note": "CPLA: Retail price declared at checkout",
                "aus_nz": "EXEMPT",
                "aus_nz_note": "National Measurement Act 1960: Price at POS",
                "japan": "EXEMPT",
                "japan_note": "Measurement Act: Price declared at point of sale",
                "oiml": "EXEMPT",
                "oiml_note": "OIML R 79: Metrology covers net content, not retail price"
            },
            {
                "parameter": "Net Quantity & Standard SI Units",
                "india": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(n): Mandatory Metric SI units (g, kg, ml, l)",
                "usa": "NON_COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "usa_note": "FPLA: Requires DUAL units (US Customary oz/lb + Metric g/kg)",
                "eu_uk": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "eu_uk_note": "Dir 76/211/EEC: Metric units mandatory + optional 'e' mark",
                "canada": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "canada_note": "CPLA Section 4: Metric quantity mandatory in EN & FR",
                "aus_nz": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "aus_nz_note": "AQS System: Metric SI units & average fill tolerance",
                "japan": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "japan_note": "Measurement Act Art 12: Metric mass/vol in Japanese SI",
                "oiml": "COMPLIANT" if "NET_QUANTITY" in dec_types else "NON_COMPLIANT",
                "oiml_note": "OIML R 79 / R 87: Standard SI metric units & fill tolerance"
            },
            {
                "parameter": "Month & Year of Packaging / Import",
                "india": "COMPLIANT" if "MONTH_YEAR" in dec_types or "EXPIRY_DATE" in dec_types else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(d): Mandatory MM/YYYY of pkg or import",
                "usa": "PARTIAL",
                "usa_note": "FDA / NIST: Mandatory for perishable goods & infant formula",
                "eu_uk": "COMPLIANT" if "MONTH_YEAR" in dec_types or "EXPIRY_DATE" in dec_types else "NON_COMPLIANT",
                "eu_uk_note": "EU Regulation 1169/2011: Expiry / Best Before mandatory",
                "canada": "COMPLIANT" if "MONTH_YEAR" in dec_types or "EXPIRY_DATE" in dec_types else "NON_COMPLIANT",
                "canada_note": "FDR B.01.007: Durable life date for goods < 90 days",
                "aus_nz": "COMPLIANT" if "MONTH_YEAR" in dec_types or "EXPIRY_DATE" in dec_types else "NON_COMPLIANT",
                "aus_nz_note": "FSANZ Code 1.2.5: Best Before / Use By mandatory",
                "japan": "COMPLIANT" if "MONTH_YEAR" in dec_types or "EXPIRY_DATE" in dec_types else "NON_COMPLIANT",
                "japan_note": "Food Labelling Standards: Expiry date mandatory",
                "oiml": "RECOMMENDED",
                "oiml_note": "OIML R 79: Standardized date marking format"
            },
            {
                "parameter": "Manufacturer / Packer Identity & Address",
                "india": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "PACKER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(a): Name & complete postal address mandatory",
                "usa": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "usa_note": "FPLA Section 500.5: Name & place of business mandatory",
                "eu_uk": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "eu_uk_note": "EU 1169/2011: FBO name & EU address mandatory",
                "canada": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "canada_note": "CPLA Section 10: Name & principal place of business",
                "aus_nz": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "aus_nz_note": "FSANZ 1.2.1: Packer / Importer name & AUS/NZ address",
                "japan": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "japan_note": "Consumer Affairs: Manufacturer/importer name & address",
                "oiml": "COMPLIANT" if "MANUFACTURER_NAME" in dec_types or "MANUFACTURER_ADDRESS" in dec_types else "NON_COMPLIANT",
                "oiml_note": "OIML R 79: Identity & address of packer/importer mandatory"
            },
            {
                "parameter": "Consumer Care Helpline & Redressal Details",
                "india": "COMPLIANT" if any(t in dec_types for t in ["CONSUMER_CARE_PHONE", "CONSUMER_CARE_EMAIL", "CONSUMER_CARE_ADDRESS", "CONSUMER_CARE_NAME"]) else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(h): Mandatory phone, email, & contact address",
                "usa": "PARTIAL",
                "usa_note": "FPLA: Street address required, helpline optional",
                "eu_uk": "PARTIAL",
                "eu_uk_note": "EU 1169/2011: FBO address required, phone optional",
                "canada": "PARTIAL",
                "canada_note": "CPLA: Address required, customer service line recommended",
                "aus_nz": "PARTIAL",
                "aus_nz_note": "FSANZ: Business contact address required",
                "japan": "PARTIAL",
                "japan_note": "CAA: Customer contact window recommended",
                "oiml": "RECOMMENDED",
                "oiml_note": "OIML R 79: Customer contact points recommended"
            },
            {
                "parameter": "Country of Origin",
                "india": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types or "IMPORTER_NAME" in dec_types else "NON_COMPLIANT",
                "india_note": "Rule 6(1)(n): Mandatory for imported & domestic commodities",
                "usa": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "usa_note": "19 U.S.C. 1304: Country of Origin mandatory on all imports",
                "eu_uk": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "eu_uk_note": "EU 1169/2011: Origin required if omission misleads",
                "canada": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "canada_note": "CPLA Art 31: Mandatory 'Product of / Made in' declaration",
                "aus_nz": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "aus_nz_note": "Country of Origin Labelling Information Standard 2016",
                "japan": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "japan_note": "Food Labelling Law: Country of origin declaration mandatory",
                "oiml": "COMPLIANT" if "COUNTRY_OF_ORIGIN" in dec_types else "NON_COMPLIANT",
                "oiml_note": "OIML R 79: Country of manufacture/origin mandatory"
            }
        ]

        # Build optical image quality defect ledger
        image_quality_findings = []
        for img in inspection.images:
            proc = img.processing_result
            if proc:
                status_val = proc.quality_status.value if hasattr(proc.quality_status, "value") else str(proc.quality_status)
                flags = proc.quality_flags or []
                is_defective = status_val in {"POOR", "UNREADABLE", "PROCESSING_FAILED"} or len(flags) > 0
                image_quality_findings.append({
                    "filename": img.original_filename,
                    "panel": img.panel_type.value if hasattr(img.panel_type, "value") else str(img.panel_type),
                    "quality_status": status_val,
                    "resolution": f"{proc.width}x{proc.height}" if proc.width and proc.height else "Standard",
                    "quality_flags": flags,
                    "is_defective": is_defective,
                    "blur_score": proc.blur_score,
                    "glare_score": proc.glare_score,
                    "justification": (
                        f"OPTICAL DEFECT DETECTED: Image quality assessed as {status_val}. Flags: {', '.join(flags) if flags else 'None'}. Unreadable panel photo prevents statutory verification of mandatory packaging declarations."
                        if is_defective else f"CLEAR OPTICAL EVIDENCE: Image quality assessed as {status_val} with zero optical defects."
                    )
                })

        if overall_compliance not in {"COMPLIANT", "NON_COMPLIANT"}:
            overall_compliance = "NON_COMPLIANT" if violations_count > 0 or any(q["is_defective"] for q in image_quality_findings) else "COMPLIANT"

        product_metadata = {
            "product_name": inspection.product_name,
            "brand_name": inspection.brand_name,
            "category": inspection.category,
            "package_type": inspection.package_type,
            "import_status": inspection.import_status.value if inspection.import_status else "DOMESTIC"
        }

        from app.rules.justifications import generate_failure_justifications
        failed_rules = [r for r in rule_evaluations if r["final_verdict"] == "FAIL"]
        guideline_failure_justifications = generate_failure_justifications(failed_rules)

        generated_at = datetime.now(timezone.utc).isoformat()
        report_payload = {
            "inspection_id": inspection.id,
            "inspection_code": inspection.inspection_code,
            "generated_at": generated_at,
            "generated_by": user.full_name or user.email,
            "overall_compliance": overall_compliance,
            "is_finalized": review.status == "FINALIZED" if review else False,
            "finalized_at": review.finalized_at.isoformat() if review and review.finalized_at else None,
            "reviewer_name": review.reviewer.full_name if review and hasattr(review, 'reviewer') and review.reviewer else user.full_name,
            "summary_notes": review.summary_notes if review else None,
            "product_metadata": product_metadata,
            "rule_evaluations": rule_evaluations,
            "hazard_explanations": hazard_explanations,
            "guideline_failure_justifications": guideline_failure_justifications,
            "guideline_justifications_formatted": "\n".join(guideline_failure_justifications),
            "image_quality_findings": image_quality_findings,
            "international_matrix": international_matrix,
            "overrides_count": overrides_count,
            "violations_count": violations_count,
            "uncertain_count": 0,
            "pass_count": pass_count,
            "declarations_summary": declarations_summary,
            "evidence": [{"image_id":img.id,"filename":img.original_filename,"sha256":img.sha256,"panel":img.panel_type.value} for img in inspection.images],
            "inspector_account_id":user.id,
            "signature_status":"UNSIGNED",
        }

        # Calculate cryptographic checksum of normalized data
        report_payload["tamper_sha256"] = compute_sha256(canonical_json_dump(report_payload))
        return report_payload

    def get_summary(self, inspection_id: str, user: User) -> ReportSummaryResponse:
        data = self.build_report_data(inspection_id, user)
        return ReportSummaryResponse(
            inspection_id=data["inspection_id"],
            inspection_code=data["inspection_code"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            generated_by=data["generated_by"],
            overall_compliance=data["overall_compliance"],
            is_finalized=data["is_finalized"],
            finalized_at=datetime.fromisoformat(data["finalized_at"]) if data["finalized_at"] else None,
            reviewer_name=data["reviewer_name"],
            summary_notes=data["summary_notes"],
            product_metadata=data["product_metadata"],
            rule_evaluations=data["rule_evaluations"],
            overrides_count=data["overrides_count"],
            violations_count=data["violations_count"],
            uncertain_count=data["uncertain_count"],
            pass_count=data["pass_count"],
            declarations_summary=data["declarations_summary"],
            tamper_sha256=data["tamper_sha256"],
            guideline_failure_justifications=data.get("guideline_failure_justifications", [])
        )

    def generate_pdf(self, inspection_id: str, user: User) -> tuple[bytes, str]:
        data = self.build_report_data(inspection_id, user)
        from app.storage.service import LocalStorageService, calculate_sha256
        from app.core.config import Settings
        storage = LocalStorageService((self.settings or Settings()).storage_local_dir)
        inspection = self._get_inspection(inspection_id, user)
        evidence = []
        for image in inspection.images:
            try: content = storage.read_file(image.storage_path)
            except FileNotFoundError as exc: raise HTTPException(409, "Evidence file missing; report generation stopped") from exc
            if calculate_sha256(content) != image.sha256:
                raise HTTPException(409, "Evidence integrity check failed; report generation stopped")
            evidence.append((image.original_filename, image.sha256, content))
        pdf_bytes = build_inspection_pdf(data, evidence)
        checksum = compute_sha256(pdf_bytes)

        # Record generated report log
        record = GeneratedReport(
            inspection_id=inspection_id,
            report_type="SUMMARY",
            format="PDF",
            status="GENERATED",
            content_sha256=checksum,
            report_data={"tamper_sha256": data["tamper_sha256"]},
            created_by_user_id=user.id
        )
        self.db.add(record)
        self.db.commit()

        filename = f"LabelSure_Report_{data['inspection_code']}_{checksum[:8]}.pdf"
        return pdf_bytes, filename

    def generate_csv(self, inspection_id: str, user: User, target: str = "rules") -> tuple[str, str]:
        data = self.build_report_data(inspection_id, user)
        if target == "declarations":
            csv_text = generate_declarations_csv(data)
            filename = f"LabelSure_Declarations_{data['inspection_code']}.csv"
        else:
            csv_text = generate_rules_csv(data)
            filename = f"LabelSure_Violations_{data['inspection_code']}.csv"

        checksum = compute_sha256(csv_text)
        record = GeneratedReport(
            inspection_id=inspection_id,
            report_type="VIOLATION_EXPORT" if target == "rules" else "DETAILED",
            format="CSV",
            status="GENERATED",
            content_sha256=checksum,
            report_data={"tamper_sha256": data["tamper_sha256"]},
            created_by_user_id=user.id
        )
        self.db.add(record)
        self.db.commit()
        return csv_text, filename

    def generate_json(self, inspection_id: str, user: User) -> tuple[str, str]:
        data = self.build_report_data(inspection_id, user)
        json_text = canonical_json_dump(data)
        checksum = compute_sha256(json_text)

        record = GeneratedReport(
            inspection_id=inspection_id,
            report_type="DETAILED",
            format="JSON",
            status="GENERATED",
            content_sha256=checksum,
            report_data=data,
            created_by_user_id=user.id
        )
        self.db.add(record)
        self.db.commit()
        filename = f"LabelSure_Snapshot_{data['inspection_code']}.json"
        return json_text, filename
