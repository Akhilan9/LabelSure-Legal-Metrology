from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.user import utc_now

if TYPE_CHECKING:
    from app.models.image_quality import ImageProcessingResult
    from app.models.inspection import Inspection, InspectionImage


class OCRStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class OCRConfidenceTier(str, Enum):
    GOOD = "GOOD"
    REVIEW = "REVIEW"
    LOW = "LOW"


class OCRRun(Base):
    __tablename__ = "ocr_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_image_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_processing_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_processing_results.id", ondelete="SET NULL"), nullable=True, index=True
    )

    engine_name: Mapped[str] = mapped_column(String(64), default="PaddleOCR", nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), default="3.7.0", nullable=False)
    language_config: Mapped[str] = mapped_column(String(32), default="en", nullable=False)

    status: Mapped[OCRStatus] = mapped_column(
        SAEnum(OCRStatus, name="ocr_status", native_enum=False, create_constraint=True, validate_strings=True),
        default=OCRStatus.PENDING, nullable=False, index=True
    )
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    block_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="ocr_runs")
    image: Mapped["InspectionImage"] = relationship("InspectionImage", back_populates="ocr_runs")
    processing_result: Mapped["ImageProcessingResult | None"] = relationship("ImageProcessingResult")
    blocks: Mapped[list["OCRBlock"]] = relationship(
        "OCRBlock", back_populates="run", cascade="all, delete-orphan",
        order_by="OCRBlock.reading_order", lazy="selectin"
    )


class OCRBlock(Base):
    __tablename__ = "ocr_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ocr_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ocr_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_image_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_images.id", ondelete="CASCADE"), nullable=False, index=True
    )

    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_tier: Mapped[OCRConfidenceTier] = mapped_column(
        SAEnum(OCRConfidenceTier, name="ocr_confidence_tier", native_enum=False, create_constraint=True, validate_strings=True),
        default=OCRConfidenceTier.GOOD, nullable=False, index=True
    )

    # 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    polygon: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)
    # Box: {x_min, y_min, x_max, y_max, width, height}
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False)

    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_order: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run: Mapped[OCRRun] = relationship("OCRRun", back_populates="blocks")
    image: Mapped["InspectionImage"] = relationship("InspectionImage")
    inspection: Mapped["Inspection"] = relationship("Inspection")
