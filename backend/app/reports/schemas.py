from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


ReportType = Literal["SUMMARY", "DETAILED", "LEGAL_NOTICE", "VIOLATION_EXPORT"]
ReportFormat = Literal["PDF", "JSON", "CSV"]


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    inspection_id: str
    inspection_code: str
    generated_at: datetime
    generated_by: str
    overall_compliance: str
    is_finalized: bool
    finalized_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    summary_notes: Optional[str] = None
    product_metadata: dict[str, Any] = {}
    rule_evaluations: list[dict[str, Any]] = []
    overrides_count: int = 0
    violations_count: int = 0
    uncertain_count: int = 0
    pass_count: int = 0
    declarations_summary: list[dict[str, Any]] = []
    tamper_sha256: str
    guideline_failure_justifications: list[str] = Field(default_factory=list)


class GeneratedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    inspection_id: str
    report_type: str
    format: str
    status: str
    content_sha256: str
    created_at: datetime
