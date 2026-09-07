from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.review.service import ReviewService
from app.review.schemas import (
    RuleDecisionRequest,
    DeclarationCorrectionRequest,
    OCRCorrectionRequest,
    FinalizeReviewRequest,
    ReopenReviewRequest,
    InspectionReviewResponse,
    RuleDecisionResponse,
    DeclarationCorrectionResponse,
    OCRCorrectionResponse,
    AuditEventResponse
)

router = APIRouter(prefix="/inspections", tags=["Human Review & Audit Trail"])


def get_review_service(request: Request, db: Session = Depends(get_session)) -> ReviewService:
    return ReviewService(db, request.app.state.settings)


@router.get("/{inspection_id}/review", response_model=InspectionReviewResponse)
def get_review(
    inspection_id: str,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    review = svc.get_or_create_review(inspection_id, user)
    return review


@router.post("/{inspection_id}/review/rule-decisions", response_model=RuleDecisionResponse)
def record_rule_decision(
    inspection_id: str,
    body: RuleDecisionRequest,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.record_rule_decision(inspection_id, user, body)


@router.post("/{inspection_id}/review/declaration-corrections", response_model=DeclarationCorrectionResponse)
def record_declaration_correction(
    inspection_id: str,
    body: DeclarationCorrectionRequest,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.record_declaration_correction(inspection_id, user, body)


@router.post("/{inspection_id}/review/ocr-corrections", response_model=OCRCorrectionResponse)
def record_ocr_correction(
    inspection_id: str,
    body: OCRCorrectionRequest,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.record_ocr_correction(inspection_id, user, body)


@router.post("/{inspection_id}/review/finalize", response_model=InspectionReviewResponse)
def finalize_review(
    inspection_id: str,
    body: FinalizeReviewRequest,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.finalize_review(inspection_id, user, body)


@router.post("/{inspection_id}/review/reopen", response_model=InspectionReviewResponse)
def reopen_review(
    inspection_id: str,
    body: ReopenReviewRequest,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.reopen_review(inspection_id, user, body)


@router.get("/{inspection_id}/audit-trail", response_model=list[AuditEventResponse])
def get_audit_trail(
    inspection_id: str,
    svc: ReviewService = Depends(get_review_service),
    user: User = Depends(get_current_user)
):
    return svc.get_audit_trail(inspection_id, user)
