from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.models.user import User, Role
from app.ocr.service import check_inspection_access
from app.extraction.service import ExtractionService
from app.extraction.schemas import CandidateResponse, RunResponse, candidate_response

router = APIRouter(prefix="/inspections", tags=["Declaration extraction"])

def service(request: Request, db: Session = Depends(get_session)):
    return ExtractionService(db, request.app.state.settings)

def access(service, inspection_id, user):
    inspection = check_inspection_access(service.db, inspection_id, user)
    if user.role == Role.INSPECTOR and inspection.created_by_user_id != user.id:
        raise HTTPException(404, "Inspection not found")

@router.post("/{inspection_id}/extract-declarations", response_model=RunResponse)
def run_extraction(inspection_id: str, svc=Depends(service), user: User=Depends(get_current_user)):
    access(svc, inspection_id, user)
    return svc.run(inspection_id, user)

@router.get("/{inspection_id}/declarations", response_model=list[CandidateResponse])
def declarations(inspection_id: str, offset: int=Query(0, ge=0), limit: int=Query(100, ge=1, le=1000),
                 svc=Depends(service), user: User=Depends(get_current_user)):
    access(svc, inspection_id, user)
    run = svc.current(inspection_id, user)
    return [candidate_response(c) for c in run.candidates[offset:offset+limit]] if run else []

@router.get("/{inspection_id}/declarations/{candidate_id}", response_model=CandidateResponse)
def declaration(inspection_id: str, candidate_id: str, svc=Depends(service), user: User=Depends(get_current_user)):
    access(svc, inspection_id, user)
    return candidate_response(svc.candidate(inspection_id, candidate_id, user))

@router.get("/{inspection_id}/extraction-summary")
def summary(inspection_id: str, svc=Depends(service), user: User=Depends(get_current_user)):
    access(svc, inspection_id, user)
    run = svc.current(inspection_id, user)
    return {"run": RunResponse.model_validate(run) if run else None,
            "candidate_count": len(run.candidates) if run else 0,
            "needs_review_count": sum(c.needs_review for c in run.candidates) if run else 0,
            "conflicting_types": sorted({c.declaration_type for c in run.candidates if "Conflicting candidates" in c.review_reasons}) if run else [],
            "message": "Machine-generated candidates; extraction does not establish legal compliance."}

