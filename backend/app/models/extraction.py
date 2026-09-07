from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import String, Text, JSON, Float, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.user import utc_now

class DeclarationType(str, Enum):
    COMMON_PRODUCT_NAME = "COMMON_PRODUCT_NAME"
    MANUFACTURER_NAME = "MANUFACTURER_NAME"
    MANUFACTURER_ADDRESS = "MANUFACTURER_ADDRESS"
    PACKER_NAME = "PACKER_NAME"
    PACKER_ADDRESS = "PACKER_ADDRESS"
    IMPORTER_NAME = "IMPORTER_NAME"
    IMPORTER_ADDRESS = "IMPORTER_ADDRESS"
    NET_QUANTITY = "NET_QUANTITY"
    MRP = "MRP"
    MONTH_YEAR = "MONTH_YEAR"
    COUNTRY_OF_ORIGIN = "COUNTRY_OF_ORIGIN"
    CONSUMER_CARE_NAME = "CONSUMER_CARE_NAME"
    CONSUMER_CARE_ADDRESS = "CONSUMER_CARE_ADDRESS"
    CONSUMER_CARE_PHONE = "CONSUMER_CARE_PHONE"
    CONSUMER_CARE_EMAIL = "CONSUMER_CARE_EMAIL"
    BARCODE_OR_GTIN = "BARCODE_OR_GTIN"
    UNIT_SALE_PRICE = "UNIT_SALE_PRICE"
    EXPIRY_DATE = "EXPIRY_DATE"
    DIMENSIONS = "DIMENSIONS"
    ECOMMERCE_SELLER = "ECOMMERCE_SELLER"
    OTHER = "OTHER"

class ExtractionMethod(str, Enum):
    REGEX = "REGEX"
    KEYWORD_CONTEXT = "KEYWORD_CONTEXT"
    SPATIAL_CONTEXT = "SPATIAL_CONTEXT"
    MULTI_BLOCK = "MULTI_BLOCK"
    MANUAL = "MANUAL"
    OPTIONAL_LLM = "OPTIONAL_LLM"

class ReviewStatus(str, Enum):
    AUTO_EXTRACTED = "AUTO_EXTRACTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class ExtractionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

def enum_column(cls, name):
    return SAEnum(cls, name=name, native_enum=False, create_constraint=True, validate_strings=True)

class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (UniqueConstraint("inspection_id", "version", "input_fingerprint", name="uq_extraction_input"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(32))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[ExtractionStatus] = mapped_column(enum_column(ExtractionStatus, "extraction_status"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    candidates: Mapped[list["DeclarationCandidate"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="DeclarationCandidate.id")

class DeclarationCandidate(Base):
    __tablename__ = "declaration_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    extraction_run_id: Mapped[str] = mapped_column(ForeignKey("extraction_runs.id", ondelete="CASCADE"), index=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    declaration_type: Mapped[DeclarationType] = mapped_column(enum_column(DeclarationType, "declaration_type"))
    raw_value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(Text)
    structured_value: Mapped[dict] = mapped_column(JSON, default=dict)
    source_ocr_run_id: Mapped[str] = mapped_column(ForeignKey("ocr_runs.id", ondelete="CASCADE"), index=True)
    source_ocr_block_id: Mapped[str] = mapped_column(ForeignKey("ocr_blocks.id", ondelete="CASCADE"))
    source_image_id: Mapped[str] = mapped_column(ForeignKey("inspection_images.id", ondelete="CASCADE"), index=True)
    panel_type: Mapped[str | None] = mapped_column(String(32))
    confidence_score: Mapped[float] = mapped_column(Float)
    confidence_factors: Mapped[dict] = mapped_column(JSON)
    extraction_method: Mapped[ExtractionMethod] = mapped_column(enum_column(ExtractionMethod, "extraction_method"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[ReviewStatus] = mapped_column(enum_column(ReviewStatus, "declaration_review_status"))
    review_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    sources: Mapped[list["DeclarationCandidateSource"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="DeclarationCandidateSource.sequence_order")

class DeclarationCandidateSource(Base):
    __tablename__ = "declaration_candidate_sources"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("declaration_candidates.id", ondelete="CASCADE"), primary_key=True)
    ocr_block_id: Mapped[str] = mapped_column(ForeignKey("ocr_blocks.id", ondelete="CASCADE"), primary_key=True)
    sequence_order: Mapped[int] = mapped_column(Integer)
    block = relationship("OCRBlock", lazy="joined")

