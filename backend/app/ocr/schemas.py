from datetime import datetime
from pydantic import BaseModel, Field

from app.models.ocr import OCRConfidenceTier, OCRStatus


class BoundingBoxDict(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    width: float
    height: float

    @property
    def x(self) -> float:
        return self.x_min

    @property
    def y(self) -> float:
        return self.y_min


class RawOCRBlockData(BaseModel):
    raw_text: str
    normalized_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    polygon: list[list[float]]  # 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    bounding_box: BoundingBoxDict
    line_number: int | None = None
    reading_order: int | None = None


class RawOCRRunResult(BaseModel):
    engine_name: str
    engine_version: str
    language_config: str
    status: OCRStatus
    average_confidence: float | None = None
    blocks: list[RawOCRBlockData] = Field(default_factory=list)
    error_code: str | None = None
    error_message_safe: str | None = None


class OCRBlockResponse(BaseModel):
    relative_box: list[float] | None = None
    id: str
    ocr_run_id: str
    inspection_id: str
    inspection_image_id: str
    block_index: int
    raw_text: str
    normalized_text: str
    confidence: float
    confidence_tier: OCRConfidenceTier
    polygon: list[list[float]]
    bounding_box: BoundingBoxDict
    line_number: int | None = None
    reading_order: int | None = None
    created_at: datetime


class OCRRunResponse(BaseModel):
    id: str
    inspection_id: str
    inspection_image_id: str
    image_processing_result_id: str | None = None
    engine_name: str
    engine_version: str
    language_config: str
    status: OCRStatus
    average_confidence: float | None = None
    block_count: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    ocr_version: str = "1"
    error_code: str | None = None
    error_message_safe: str | None = None
    blocks: list[OCRBlockResponse] = Field(default_factory=list)


class BatchOCRResponse(BaseModel):
    inspection_id: str
    total_images: int
    success: int
    partial: int
    failed: int
    results: list[OCRRunResponse] = Field(default_factory=list)


class InspectionOCRSummaryPanel(BaseModel):
    panel_type: str
    image_id: str
    ocr_run_id: str | None = None
    status: OCRStatus | None = None
    block_count: int = 0
    average_confidence: float | None = None
    text_lines: list[str] = Field(default_factory=list)


class InspectionOCRSummary(BaseModel):
    inspection_id: str
    inspection_code: str
    total_images: int
    images_processed: int
    ocr_completed_count: int
    ocr_failed_count: int
    total_ocr_blocks: int
    average_confidence: float | None = None
    panels: list[InspectionOCRSummaryPanel] = Field(default_factory=list)
