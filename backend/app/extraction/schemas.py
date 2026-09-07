from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.extraction import DeclarationType, ExtractionMethod, ReviewStatus, ExtractionStatus

class SourceResponse(BaseModel):
    ocr_block_id: str
    sequence_order: int
    raw_text: str
    polygon: list
    bounding_box: dict

class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    extraction_run_id: str
    inspection_id: str
    declaration_type: DeclarationType
    raw_value: str
    normalized_value: str
    structured_value: dict
    source_ocr_run_id: str
    source_ocr_block_id: str
    source_image_variant: str
    source_image_id: str
    panel_type: str | None
    confidence_score: float
    confidence_factors: dict
    extraction_method: ExtractionMethod
    is_primary: bool
    needs_review: bool
    review_status: ReviewStatus
    review_reasons: list[str]
    created_at: datetime
    updated_at: datetime
    sources: list[SourceResponse]

class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    inspection_id: str
    version: str
    status: ExtractionStatus
    started_at: datetime
    completed_at: datetime | None
    candidate_count: int
    error_code: str | None
    warnings: list[str]

def candidate_response(candidate):
    values = {name: getattr(candidate, name) for name in CandidateResponse.model_fields if name not in {"sources", "source_image_variant"}}
    values["source_image_variant"] = candidate.structured_value.get("_source_image_variant", "original")
    values["sources"] = [SourceResponse(ocr_block_id=s.ocr_block_id, sequence_order=s.sequence_order,
        raw_text=s.block.raw_text, polygon=s.block.polygon, bounding_box=s.block.bounding_box) for s in candidate.sources]
    return CandidateResponse(**values)

