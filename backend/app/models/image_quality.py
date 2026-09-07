from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.user import utc_now


class QualityStatus(str, Enum):
    PENDING = "PENDING"
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    POOR = "POOR"
    UNREADABLE = "UNREADABLE"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class QualityFlag(str, Enum):
    BLURRY = "BLURRY"
    TOO_DARK = "TOO_DARK"
    TOO_BRIGHT = "TOO_BRIGHT"
    LOW_CONTRAST = "LOW_CONTRAST"
    LOW_RESOLUTION = "LOW_RESOLUTION"
    POSSIBLE_GLARE = "POSSIBLE_GLARE"
    INVALID_IMAGE = "INVALID_IMAGE"
    PROCESSING_ERROR = "PROCESSING_ERROR"


class ImageProcessingResult(Base):
    __tablename__ = "image_processing_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_image_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_images.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int | None] = mapped_column(Integer, nullable=True)

    blur_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    contrast_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    glare_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    quality_status: Mapped[QualityStatus] = mapped_column(
        SAEnum(QualityStatus, name="quality_status", native_enum=False,
               create_constraint=True, validate_strings=True),
        default=QualityStatus.PENDING, nullable=False, index=True
    )
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    derived_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    derived_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    derived_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    processing_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    image: Mapped["InspectionImage"] = relationship("InspectionImage", back_populates="processing_result")
