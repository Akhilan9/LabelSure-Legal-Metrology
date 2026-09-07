from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.image_processing.schemas import ImageQualityResponse
from app.models.inspection import ImportStatus, InspectionStatus, PanelType


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class InspectionImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    sha256: str
    panel_type: PanelType
    upload_order: int
    width: int | None = None
    height: int | None = None
    quality_status: str | None = None
    created_at: datetime
    uploaded_by_user_id: str
    content_url: str = ""
    processing_result: ImageQualityResponse | None = None

    @field_validator("created_at")
    @classmethod
    def utc_dates(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class InspectionImageUpdate(BaseModel):
    panel_type: PanelType | None = None
    upload_order: int | None = Field(default=None, ge=0)


class InspectionCreate(BaseModel):
    client_id: UUID | None = None
    product_name: str | None = Field(default=None, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    package_type: str | None = Field(default=None, max_length=100)
    import_status: ImportStatus = ImportStatus.UNKNOWN
    barcode: str | None = Field(default=None, max_length=64)
    manufacturer_name: str | None = Field(default=None, max_length=255)
    packer_name: str | None = Field(default=None, max_length=255)
    importer_name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class InspectionUpdate(BaseModel):
    product_name: str | None = Field(default=None, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    package_type: str | None = Field(default=None, max_length=100)
    import_status: ImportStatus | None = None
    barcode: str | None = Field(default=None, max_length=64)
    manufacturer_name: str | None = Field(default=None, max_length=255)
    packer_name: str | None = Field(default=None, max_length=255)
    importer_name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class InspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_code: str
    created_by_user_id: str
    created_by_name: str | None = None
    assigned_to_user_id: str | None = None
    assigned_to_name: str | None = None
    status: InspectionStatus
    product_name: str | None = None
    brand_name: str | None = None
    category: str | None = None
    package_type: str | None = None
    import_status: ImportStatus | None = None
    barcode: str | None = None
    manufacturer_name: str | None = None
    packer_name: str | None = None
    importer_name: str | None = None
    notes: str | None = None
    images_count: int = 0
    images: list[InspectionImageResponse] = []
    international_ban_info: dict | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None

    @field_validator("created_at", "updated_at", "submitted_at")
    @classmethod
    def utc_dates(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)


class InspectionListResponse(BaseModel):
    items: list[InspectionResponse]
    total: int
    page: int
    page_size: int


class DashboardSummaryResponse(BaseModel):
    total_inspections: int
    draft_count: int
    evidence_uploaded_count: int
    ready_for_analysis_count: int
    recent_inspections: list[InspectionResponse]
    guideline_failure_justifications: list[str] = Field(default_factory=list)
