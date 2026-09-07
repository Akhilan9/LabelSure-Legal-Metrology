from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class ViolationStat(BaseModel):
    rule_key: str
    title: str
    severity: str
    count: int
    legal_reference: str | None = None


class CategoryStat(BaseModel):
    category: str
    total: int
    compliant: int
    non_compliant: int
    uncertain: int


class UrgencyQueueItem(BaseModel):
    inspection_id: str
    inspection_code: str
    product_name: str | None = None
    brand_name: str | None = None
    category: str | None = None
    package_type: str | None = None
    status: str
    overall_compliance: str
    review_status: str
    urgency_score: float
    urgency_tier: str
    violation_count: int
    uncertain_count: int
    pass_count: int
    override_count: int
    images_count: int
    created_at: datetime
    created_by_name: str | None = None
    days_pending: int


class ReviewQueueResponse(BaseModel):
    items: list[UrgencyQueueItem]
    total: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class EnforcementMetricsResponse(BaseModel):
    total_inspections: int
    draft_count: int
    evidence_uploaded_count: int
    ready_for_analysis_count: int
    finalized_count: int
    compliant_count: int
    non_compliant_count: int
    uncertain_count: int
    compliance_percentage: float
    total_overrides: int
    total_violations: int
    top_violations: list[ViolationStat]
    category_breakdown: list[CategoryStat]
    guideline_failure_justifications: list[str] = Field(default_factory=list)


class AnalyticsTrendsResponse(BaseModel):
    category_compliance: list[CategoryStat]
    package_type_distribution: list[dict]
    average_ocr_confidence: float
    total_reviewed: int
    total_overridden: int
    override_rate_percentage: float
