import csv
import io
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_role
from app.context.service import ContextService
from app.db.session import get_session
from app.extraction.service import ExtractionService
from app.models.inspection import (
    ImportStatus,
    Inspection,
    InspectionImage,
    InspectionStatus,
    PanelType,
)
from app.models.rules import RuleEvaluationRun
from app.models.user import Role, User
from app.ocr.service import OCRService
from app.reports.consolidated_pdf import build_consolidated_center_pdf
from app.reports.exporter import canonical_json_dump, compute_sha256
from app.image_processing.pipeline import ImageProcessingPipeline
from app.models.image_quality import ImageProcessingResult
from app.review.schemas import FinalizeReviewRequest
from app.review.service import ReviewService
from app.rules.engine import RuleEngine
from app.rules.justifications import generate_failure_justifications, format_failure_justifications
from app.rules.schemas import EvaluateRequest
from app.services.inspection import generate_inspection_code
from app.storage.service import LocalStorageService, calculate_sha256, detect_and_validate_image

router = APIRouter(prefix="/inspection-center", tags=["Inspection Center Multi-Item Sessions"])


class ConsolidatedReportRequest(BaseModel):
    center_name: str
    category: str
    location: str
    session_code: Optional[str] = None
    inspection_ids: list[str] = Field(default_factory=list)
    items_data: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/analyze-item")
async def analyze_center_item(
    request: Request,
    center_name: str = Form(...),
    category: str = Form("General"),
    location: str = Form("Not Specified"),
    product_name: Optional[str] = Form(None),
    brand_name: Optional[str] = Form(None),
    panel_type: str = Form("FRONT"),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
):
    """
    Ingests one commodity (with 1 or more photos) under an active Inspection Center drive.
    Executes automated OCR, extraction, and statutory rule evaluation immediately.
    """
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No evidence photo provided.")

    settings = request.app.state.settings
    code = generate_inspection_code(session)
    auto_name = product_name or f"Commodity Item ({files[0].filename or 'Photo'})"

    insp = Inspection(
        id=str(uuid4()),
        inspection_code=code,
        created_by_user_id=current_user.id,
        assigned_to_user_id=current_user.id,
        status=InspectionStatus.DRAFT,
        product_name=auto_name,
        brand_name=brand_name,
        category=category,
        package_type="Standard Package",
        import_status=ImportStatus.DOMESTIC,
        notes=f"Inspection Center: {center_name} | Location: {location} | Drive Category: {category}",
    )
    session.add(insp)
    session.commit()
    session.refresh(insp)

    storage = LocalStorageService(settings.storage_local_dir)
    images_saved = []

    for idx, f in enumerate(files):
        contents = await f.read()
        if len(contents) == 0:
            continue
        try:
            mime_type, ext = detect_and_validate_image(contents, f.filename or "photo.jpg")
        except Exception:
            continue

        sha = calculate_sha256(contents)
        stored_filename, storage_path = storage.generate_storage_path(insp.id, ext)
        storage.save_file(storage_path, contents)
        panel_enum = getattr(PanelType, panel_type.upper(), PanelType.FRONT)

        img_obj = InspectionImage(
            id=str(uuid4()),
            inspection_id=insp.id,
            original_filename=f.filename or f"item_{idx + 1}{ext}",
            stored_filename=stored_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=len(contents),
            sha256=sha,
            panel_type=panel_enum,
            upload_order=idx,
            uploaded_by_user_id=current_user.id,
        )
        session.add(img_obj)
        session.flush()

        # Run Phase 4 Image Processing & Quality Analysis
        try:
            pipeline = ImageProcessingPipeline(settings, storage)
            decoded = pipeline.preprocessor.decode_and_orient(contents)
            assessed = pipeline.analyzer.analyze(decoded)
            img_obj.width = assessed.width
            img_obj.height = assessed.height
            img_obj.quality_status = assessed.status.value
            session.add(ImageProcessingResult(
                inspection_image_id=img_obj.id,
                width=assessed.width,
                height=assessed.height,
                channels=assessed.channels,
                blur_score=assessed.blur_score,
                brightness_score=assessed.brightness_score,
                contrast_score=assessed.contrast_score,
                glare_score=assessed.glare_score,
                quality_status=assessed.status,
                quality_flags=assessed.flags,
                processing_version=settings.image_pipeline_version,
            ))
        except Exception:
            pass

        images_saved.append(img_obj)

    insp.status = InspectionStatus.EVIDENCE_UPLOADED
    session.commit()
    session.refresh(insp)

    from app.api.analysis import analyze

    failure_justifications = []
    rule_verdict = "NON_COMPLIANT"
    violations_count = 0

    detected_color_marks = []
    try:
        analysis_res = analyze(insp.id, request, session, current_user)
        if isinstance(analysis_res, dict):
            detected_color_marks = analysis_res.get("detected_color_marks", [])
        final_verdict = analysis_res.get("final_compliance_status", "NON_COMPLIANT")
        rule_verdict = "COMPLIANT" if final_verdict in ("COMPLIANT", "PASS") else "NON_COMPLIANT"
        eval_data = analysis_res.get("evaluation", {})
        fail_count = eval_data.get("fail_count", 0)
        uncertain_count = eval_data.get("uncertain_count", 0)
        violations_count = fail_count + uncertain_count
        failure_justifications = eval_data.get("guideline_failure_justifications", [])
        if rule_verdict == "NON_COMPLIANT" and not failure_justifications:
            failure_justifications = generate_failure_justifications(["R-LMPC-RULE6-MFG"])
        elif rule_verdict == "COMPLIANT":
            violations_count = 0
            failure_justifications = []
    except HTTPException as exc:
        rule_verdict = "NON_COMPLIANT"
        violations_count = 1
        failure_justifications = [
            f"[LM-0001 Violation]: PCR Rule 6(1) FAIL: {exc.detail}"
        ]
    except Exception:
        rule_verdict = "NON_COMPLIANT"
        violations_count = 1
        failure_justifications = generate_failure_justifications(["R-LMPC-RULE6-MFG"])

    session.refresh(insp)
    insp.status = InspectionStatus.COMPLIANT if rule_verdict == "COMPLIANT" else InspectionStatus.NON_COMPLIANT
    insp.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.commit()

    from app.services.banned_products import check_international_bans
    ban_info = check_international_bans(insp.product_name)

    return {
        "inspection_id": insp.id,
        "inspection_code": insp.inspection_code,
        "product_name": insp.product_name,
        "brand_name": insp.brand_name or "",
        "category": insp.category,
        "verdict": rule_verdict,
        "status": insp.status.value,
        "violations_count": violations_count,
        "guideline_failure_justifications": failure_justifications,
        "international_ban_info": ban_info,
        "detected_color_marks": detected_color_marks,
        "images_count": len(images_saved),
        "created_at": insp.created_at.isoformat(),
    }


def _build_consolidated_payload(payload: ConsolidatedReportRequest, user: User, session: Session) -> dict:
    from app.services.banned_products import check_international_bans
    session_code = payload.session_code or f"IC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:6].upper()}"
    items: list[dict] = []
    seen_ids = set()

    # Load from DB if inspection_ids provided
    if payload.inspection_ids:
        records = session.scalars(
            select(Inspection).where(Inspection.id.in_(payload.inspection_ids))
        ).all()
        for rec in records:
            seen_ids.add(rec.id)
            latest_run = session.scalar(
                select(RuleEvaluationRun)
                .where(RuleEvaluationRun.inspection_id == rec.id)
                .order_by(RuleEvaluationRun.created_at.desc())
            )
            v = "COMPLIANT" if rec.status == InspectionStatus.COMPLIANT else "NON_COMPLIANT"
            justifications = []
            viols_list = []
            if latest_run:
                v = latest_run.overall
                failed = [r for r in latest_run.results if r.verdict == "FAIL"]
                justifications = generate_failure_justifications(failed)
                viols_list = [f"[{r.rule_key}]" for r in failed]
            elif v == "NON_COMPLIANT":
                justifications = generate_failure_justifications(["R-LMPC-RULE6-MFG"])
                viols_list = ["[R-LMPC-RULE6-MFG]"]

            from app.core.config import get_settings
            from app.services.color_marks import scan_inspection_color_marks
            cmarks = scan_inspection_color_marks(rec.id, get_settings().storage_local_dir)
            item_ban_info = check_international_bans(rec.product_name)

            items.append({
                "inspection_id": rec.id,
                "inspection_code": rec.inspection_code,
                "product_name": rec.product_name or "Commodity Item",
                "brand_name": rec.brand_name or "",
                "category": rec.category or payload.category,
                "verdict": v,
                "violations_count": len(viols_list),
                "violations": viols_list,
                "failure_justifications": justifications,
                "international_ban_info": item_ban_info,
                "detected_color_marks": cmarks,
                "created_at": rec.created_at.isoformat(),
            })

    # Merge any additional client-staged items data
    for d in payload.items_data:
        iid = d.get("inspection_id")
        if iid and iid in seen_ids:
            continue
        items.append({
            "inspection_id": iid or str(uuid4()),
            "inspection_code": d.get("inspection_code") or f"INSP-{str(uuid4())[:8].upper()}",
            "product_name": d.get("product_name") or "Commodity Item",
            "brand_name": d.get("brand_name") or "",
            "category": d.get("category") or payload.category,
            "verdict": d.get("verdict") or "NON_COMPLIANT",
            "violations_count": d.get("violations_count") or 0,
            "violations": d.get("violations") or [],
            "failure_justifications": d.get("guideline_failure_justifications") or [],
            "international_ban_info": d.get("international_ban_info"),
            "detected_color_marks": d.get("detected_color_marks") or [],
            "created_at": d.get("created_at") or datetime.now(timezone.utc).isoformat(),
        })

    total_items = len(items)
    compliant_count = sum(1 for itm in items if itm.get("verdict") == "COMPLIANT")
    non_compliant_count = total_items - compliant_count
    rate_val = (compliant_count / total_items * 100.0) if total_items > 0 else 100.0
    compliance_rate = f"{rate_val:.1f}%"
    overall_verdict = "COMPLIANT" if (non_compliant_count == 0 and total_items > 0) else "NON_COMPLIANT"

    # Aggregated unique failure justifications across all violating items
    aggregated_justifications: list[str] = []
    seen_justs: set[str] = set()
    total_violations = 0

    for itm in items:
        if itm.get("verdict") != "COMPLIANT":
            total_violations += max(1, itm.get("violations_count", 1))
            for j in itm.get("failure_justifications", []):
                if j not in seen_justs and "[LM-0016" not in j:
                    seen_justs.add(j)
                    aggregated_justifications.append(j)

    if aggregated_justifications:
        # Append Section 36(1) penalty justification
        from app.rules.justifications import PENALTY_JUSTIFICATION
        aggregated_justifications.append(PENALTY_JUSTIFICATION)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_payload = {
        "center_name": payload.center_name,
        "category": payload.category,
        "location": payload.location,
        "session_code": session_code,
        "generated_at": generated_at,
        "generated_by": user.full_name or user.email,
        "overall_verdict": overall_verdict,
        "total_items": total_items,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "total_violations": total_violations,
        "compliance_rate": compliance_rate,
        "guideline_failure_justifications": aggregated_justifications,
        "guideline_justifications_formatted": format_failure_justifications(aggregated_justifications),
        "items": items,
    }

    report_payload["tamper_sha256"] = compute_sha256(canonical_json_dump(report_payload))
    return report_payload


@router.post("/consolidated-report")
def get_consolidated_report(
    payload: ConsolidatedReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Returns consolidated audit report summary data for an Inspection Center session.
    """
    return _build_consolidated_payload(payload, current_user, session)


@router.post("/consolidated-report/pdf")
def download_consolidated_pdf(
    payload: ConsolidatedReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Generates and streams the official Consolidated Inspection Center ReportLab PDF.
    """
    report_data = _build_consolidated_payload(payload, current_user, session)
    pdf_bytes = build_consolidated_center_pdf(report_data)
    filename = f"LabelSure_Inspection_Center_Report_{report_data['session_code']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/consolidated-report/csv")
def download_consolidated_csv(
    payload: ConsolidatedReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Generates and streams RFC-4180 CSV export of all inspected items in the center session.
    """
    report_data = _build_consolidated_payload(payload, current_user, session)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")

    # Header metadata
    writer.writerow(["# LABELSURE CONSOLIDATED INSPECTION CENTER REPORT"])
    writer.writerow(["Center Name", report_data["center_name"]])
    writer.writerow(["Category", report_data["category"]])
    writer.writerow(["Location", report_data["location"]])
    writer.writerow(["Drive Code", report_data["session_code"]])
    writer.writerow(["Generated At", report_data["generated_at"]])
    writer.writerow(["Inspecting Officer", report_data["generated_by"]])
    writer.writerow(["Overall Status", report_data["overall_verdict"]])
    writer.writerow(["Compliance Rate", report_data["compliance_rate"]])
    writer.writerow(["Tamper Seal (SHA-256)", report_data["tamper_sha256"]])
    writer.writerow([])

    # Items table
    writer.writerow(["Item #", "Product Name", "Brand Name", "Category", "Verdict", "Violations Count", "Violations Details", "Inspection Code", "Timestamp"])
    for idx, itm in enumerate(report_data["items"], start=1):
        writer.writerow([
            idx,
            itm.get("product_name"),
            itm.get("brand_name"),
            itm.get("category"),
            itm.get("verdict"),
            itm.get("violations_count"),
            "; ".join(itm.get("failure_justifications", [])),
            itm.get("inspection_code"),
            itm.get("created_at"),
        ])

    csv_text = buffer.getvalue()
    filename = f"LabelSure_Inspection_Center_Items_{report_data['session_code']}.csv"

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
