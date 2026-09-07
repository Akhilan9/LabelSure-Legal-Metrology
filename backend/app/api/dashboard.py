from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.inspections import to_inspection_response
from app.db.session import get_session
from app.models.inspection import Inspection, InspectionStatus
from app.models.user import Role, User
from app.schemas.inspection import DashboardSummaryResponse
from app.dashboard.schemas import (
    EnforcementMetricsResponse,
    ReviewQueueResponse,
    AnalyticsTrendsResponse
)
from app.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Enforcement Dashboard & Analytics"])


def get_dashboard_service(session: Session = Depends(get_session)) -> DashboardService:
    return DashboardService(session)


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DashboardSummaryResponse:
    base_filter = []
    if current_user.role == Role.INSPECTOR:
        base_filter.append(
            or_(
                Inspection.created_by_user_id == current_user.id,
                Inspection.assigned_to_user_id == current_user.id,
            )
        )

    total_query = select(func.count(Inspection.id))
    if base_filter:
        total_query = total_query.where(*base_filter)
    total_inspections = session.scalar(total_query) or 0

    draft_query = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.DRAFT)
    if base_filter:
        draft_query = draft_query.where(*base_filter)
    draft_count = session.scalar(draft_query) or 0

    uploaded_query = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.EVIDENCE_UPLOADED)
    if base_filter:
        uploaded_query = uploaded_query.where(*base_filter)
    evidence_uploaded_count = session.scalar(uploaded_query) or 0

    ready_query = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.READY_FOR_ANALYSIS)
    if base_filter:
        ready_query = ready_query.where(*base_filter)
    ready_for_analysis_count = session.scalar(ready_query) or 0

    recent_query = select(Inspection)
    if base_filter:
        recent_query = recent_query.where(*base_filter)
    recent_query = recent_query.order_by(Inspection.created_at.desc()).limit(5)
    recent_records = session.scalars(recent_query).all()

    recent_inspections = [to_inspection_response(insp) for insp in recent_records]

    from app.models.rules import RuleEvaluationRun
    from app.rules.justifications import generate_failure_justifications
    recent_runs = session.scalars(
        select(RuleEvaluationRun).order_by(RuleEvaluationRun.created_at.desc()).limit(10)
    ).all()
    failed_keys = []
    for run in recent_runs:
        for res in run.results:
            if res.verdict in {"FAIL", "UNCERTAIN"}:
                failed_keys.append(res.rule_key)
    guideline_justifications = generate_failure_justifications(failed_keys)

    return DashboardSummaryResponse(
        total_inspections=total_inspections,
        draft_count=draft_count,
        evidence_uploaded_count=evidence_uploaded_count,
        ready_for_analysis_count=ready_for_analysis_count,
        recent_inspections=recent_inspections,
        guideline_failure_justifications=guideline_justifications,
    )


@router.get("/metrics", response_model=EnforcementMetricsResponse)
def get_enforcement_metrics(
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(get_dashboard_service)
) -> EnforcementMetricsResponse:
    return svc.get_enforcement_metrics(current_user)


@router.get("/review-queue", response_model=ReviewQueueResponse)
def get_review_queue(
    status: str = Query("ALL", description="Filter by status (ALL, NEEDS_REVIEW, UNDER_REVIEW, FINALIZED)"),
    category: str | None = Query(None, description="Filter by product category"),
    urgency: str = Query("ALL", description="Filter by urgency tier (ALL, CRITICAL, HIGH, MEDIUM, LOW)"),
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(get_dashboard_service)
) -> ReviewQueueResponse:
    return svc.get_review_queue(
        user=current_user,
        status_filter=status,
        category_filter=category,
        urgency_filter=urgency
    )


@router.get("/analytics", response_model=AnalyticsTrendsResponse)
def get_analytics_trends(
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(get_dashboard_service)
) -> AnalyticsTrendsResponse:
    return svc.get_analytics_trends(current_user)
