from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.image_quality import QualityStatus


class ImageQualityMetrics(BaseModel):
    blur_score: float | None = Field(default=None, description="Variance of Laplacian focus metric")
    brightness_score: float | None = Field(default=None, description="Mean grayscale luminance (0-255)")
    contrast_score: float | None = Field(default=None, description="Standard deviation of grayscale intensity")
    glare_score: float | None = Field(default=None, description="Ratio of high-intensity near-white pixels (0.0-1.0)")


class ImageQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_image_id: str
    quality_status: QualityStatus
    width: int
    height: int
    channels: int | None = None
    metrics: ImageQualityMetrics
    flags: list[str] = Field(default_factory=list)
    processing_version: str = "1"
    derived_image_available: bool = False
    derived_content_url: str | None = None
    derived_sha256: str | None = None
    error_message: str | None = None
    processed_at: datetime


class BatchProcessImagesResponse(BaseModel):
    total_processed: int
    successful_count: int
    failed_count: int
    results: list[ImageQualityResponse]
