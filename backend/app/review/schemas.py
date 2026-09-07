from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


VerdictType = Literal["PASS", "FAIL", "UNCERTAIN", "NOT_APPLICABLE"]
ReviewStatus = Literal["DRAFT", "FINALIZED", "REOPENED"]
FinalComplianceStatus = Literal["COMPLIANT", "NON_COMPLIANT", "CONDITIONAL_COMPLIANCE", "REJECTED"]
CorrectionAction = Literal["CONFIRMED", "CORRECTED", "REJECTED", "MANUALLY_ADDED"]


class RuleDecisionRequest(StrictModel):
    rule_id: str = Field(min_length=1, max_length=64)
    rule_key: str = Field(min_length=1, max_length=64)
    final_verdict: VerdictType
    override_reason: Optional[str] = Field(None, max_length=2000)
    reviewer_notes: Optional[str] = Field(None, max_length=2000)


class DeclarationCorrectionRequest(StrictModel):
    candidate_id: Optional[str] = Field(None, max_length=36)
    declaration_type: str = Field(min_length=1, max_length=64)
    original_raw_value: Optional[str] = Field(None, max_length=2000)
    original_normalized_value: Optional[str] = Field(None, max_length=2000)
    corrected_value: str = Field(min_length=1, max_length=2000)
    action: CorrectionAction
    correction_reason: str = Field(min_length=3, max_length=2000)


class OCRCorrectionRequest(StrictModel):
    ocr_block_id: Optional[str] = Field(None, max_length=36)
    inspection_image_id: Optional[str] = Field(None, max_length=36)
    original_text: Optional[str] = Field(None, max_length=2000)
    corrected_text: str = Field(min_length=1, max_length=2000)
    action: CorrectionAction
    correction_reason: str = Field(min_length=3, max_length=2000)


class FinalizeReviewRequest(StrictModel):
    final_compliance_status: FinalComplianceStatus
    summary_notes: Optional[str] = Field(None, max_length=4000)


class ReopenReviewRequest(StrictModel):
    reopen_reason: str = Field(min_length=5, max_length=2000)


class RuleDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    review_id: str
    rule_id: str
    rule_key: str
    original_verdict: str
    final_verdict: str
    is_overridden: bool
    override_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DeclarationCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    review_id: str
    candidate_id: Optional[str] = None
    declaration_type: str
    original_raw_value: Optional[str] = None
    original_normalized_value: Optional[str] = None
    corrected_value: str
    action: str
    correction_reason: str
    created_at: datetime


class OCRCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    review_id: str
    ocr_block_id: Optional[str] = None
    inspection_image_id: Optional[str] = None
    original_text: Optional[str] = None
    corrected_text: str
    action: str
    correction_reason: str
    created_at: datetime


class InspectionReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    inspection_id: str
    reviewer_user_id: str
    reviewer_name: Optional[str] = None
    status: str
    final_compliance_status: Optional[str] = None
    summary_notes: Optional[str] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    rule_decisions: list[RuleDecisionResponse] = []
    declaration_corrections: list[DeclarationCorrectionResponse] = []
    ocr_corrections: list[OCRCorrectionResponse] = []


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    inspection_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
