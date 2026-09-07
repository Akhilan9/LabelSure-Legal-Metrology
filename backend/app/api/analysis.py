from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.ocr.service import OCRService, check_inspection_access
from app.storage.service import LocalStorageService
from app.extraction.service import ExtractionService
from app.context.service import ContextService
from app.rules.engine import RuleEngine
from app.rules.schemas import EvaluateRequest
from app.review.service import ReviewService
from app.review.schemas import FinalizeReviewRequest
from app.models.inspection import InspectionStatus
from app.models.review import InspectionReview
from sqlalchemy import select

router = APIRouter(prefix='/inspections', tags=['Analysis'])

@router.post('/{inspection_id}/analysis')
def analyze(inspection_id: str, request: Request, db: Session=Depends(get_session), user=Depends(get_current_user)):
    inspection = check_inspection_access(db, inspection_id, user)
    if inspection.created_by_user_id != user.id:
        raise HTTPException(403, 'Only the inspection owner can analyze this case')
    if not inspection.images:
        raise HTTPException(422, 'This case has no saved photos. Add evidence to this inspection first.')

    review = db.scalar(select(InspectionReview).where(InspectionReview.inspection_id==inspection_id).order_by(InspectionReview.created_at.desc()))
    if review and review.status == 'FINALIZED':
        # Auto-reopen if re-analyzing
        ReviewService(db, request.app.state.settings).reopen_review(
            inspection_id, user, type('ReopenReq', (), {'reopen_reason': 'Automated re-analysis requested by inspector'})()
        )

    settings = request.app.state.settings
    ocr = OCRService(db, settings, LocalStorageService(settings.storage_local_dir)).batch_process_inspection_ocr(inspection_id, user)
    if not any(run.block_count for run in ocr.results):
        raise HTTPException(422, 'Photos are saved, but no readable text was found. Retake an unclear photo or retry analysis.')

    extraction = ExtractionService(db, settings).run(inspection_id, user)
    ContextService(db, settings).run(inspection_id, user)
    evaluation = RuleEngine(db, settings).evaluate(inspection_id, user, EvaluateRequest(allow_prototype_rules=True))

    fail_count = evaluation.get('fail_count', 0)
    pass_count = evaluation.get('pass_count', 0)
    final_status = 'NON_COMPLIANT' if fail_count > 0 else ('COMPLIANT' if pass_count > 0 else 'UNCERTAIN')

    # Auto-finalize review so end-product PDF and final verdict are immediately ready
    rev_svc = ReviewService(db, settings)
    finalized_review = rev_svc.finalize_review(
        inspection_id,
        user,
        FinalizeReviewRequest(
            final_compliance_status=final_status,
            summary_notes=f"Automated Legal Metrology evaluation completed. {pass_count} rules passed, {fail_count} violations detected."
        )
    )

    if final_status == 'COMPLIANT':
        inspection.status = InspectionStatus.COMPLIANT
    elif final_status == 'NON_COMPLIANT':
        inspection.status = InspectionStatus.NON_COMPLIANT
    else:
        inspection.status = InspectionStatus.REVIEW_REQUIRED
    db.commit()

    from app.services.banned_products import check_international_bans
    prod_name = inspection.product_name
    if not prod_name and getattr(extraction, 'candidates', None):
        for c in extraction.candidates:
            if getattr(c, 'declaration_type', None) == 'COMMON_PRODUCT_NAME' and getattr(c, 'normalized_value', None):
                prod_name = c.normalized_value
                break
    ban_info = check_international_bans(prod_name)

    return {
        'inspection_id': inspection_id,
        'status': inspection.status,
        'final_compliance_status': final_status,
        'ocr': {'success': ocr.success, 'partial': ocr.partial, 'failed': ocr.failed},
        'candidate_count': extraction.candidate_count,
        'evaluation': evaluation,
        'international_ban_info': ban_info,
    }


@router.post('/bulk-analysis')
def bulk_analyze(payload: dict, request: Request, db: Session=Depends(get_session), user=Depends(get_current_user)):
    inspection_ids = payload.get('inspection_ids', [])
    results = []
    for i_id in inspection_ids:
        try:
            res = analyze(i_id, request, db, user)
            results.append({'inspection_id': i_id, 'status': 'SUCCESS', 'final_compliance_status': res.get('final_compliance_status')})
        except Exception as e:
            results.append({'inspection_id': i_id, 'status': 'FAILED', 'error': str(e)})
    return {'total': len(inspection_ids), 'results': results}


