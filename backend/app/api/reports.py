from fastapi import APIRouter, Depends, Request, Response, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.reports.service import ReportService
from app.reports.schemas import ReportSummaryResponse

router = APIRouter(prefix="/inspections", tags=["Reports & Statutory Exports"])


def get_report_service(request: Request, db: Session = Depends(get_session)) -> ReportService:
    return ReportService(db, request.app.state.settings)


@router.get("/{inspection_id}/reports/summary", response_model=ReportSummaryResponse)
def get_report_summary(
    inspection_id: str,
    svc: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user)
):
    return svc.get_summary(inspection_id, user)


@router.get("/{inspection_id}/reports/pdf")
def download_report_pdf(
    inspection_id: str,
    svc: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user)
):
    pdf_bytes, filename = svc.generate_pdf(inspection_id, user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{inspection_id}/reports/csv")
def download_report_csv(
    inspection_id: str,
    target: str = Query("rules", description="Export target: 'rules' or 'declarations'"),
    svc: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user)
):
    csv_text, filename = svc.generate_csv(inspection_id, user, target=target)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{inspection_id}/reports/json")
def download_report_json(
    inspection_id: str,
    svc: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user)
):
    json_text, filename = svc.generate_json(inspection_id, user)
    return Response(
        content=json_text,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
