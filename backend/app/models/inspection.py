from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.user import User, utc_now

if TYPE_CHECKING:
    from app.models.image_quality import ImageProcessingResult
    from app.models.ocr import OCRRun


class InspectionStatus(str, Enum):
    DRAFT = "DRAFT"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNCERTAIN = "UNCERTAIN"
    FINALIZED = "FINALIZED"


class ImportStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    DOMESTIC = "DOMESTIC"
    IMPORTED = "IMPORTED"


class PanelType(str, Enum):
    FRONT = "FRONT"
    BACK = "BACK"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    DECLARATION_PANEL = "DECLARATION_PANEL"
    MRP_PANEL = "MRP_PANEL"
    OTHER = "OTHER"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[InspectionStatus] = mapped_column(
        SAEnum(InspectionStatus, name="inspection_status", native_enum=False,
               create_constraint=True, validate_strings=True),
        default=InspectionStatus.DRAFT, nullable=False, index=True
    )
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    import_status: Mapped[ImportStatus | None] = mapped_column(
        SAEnum(ImportStatus, name="import_status", native_enum=False,
               create_constraint=True, validate_strings=True),
        default=ImportStatus.UNKNOWN, nullable=True
    )
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    manufacturer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    packer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    importer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[User] = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")
    assigned_to: Mapped[User | None] = relationship("User", foreign_keys=[assigned_to_user_id], lazy="joined")
    images: Mapped[list["InspectionImage"]] = relationship(
        "InspectionImage", back_populates="inspection", cascade="all, delete-orphan",
        order_by="InspectionImage.upload_order", lazy="selectin"
    )
    ocr_runs: Mapped[list["OCRRun"]] = relationship(
        "OCRRun", back_populates="inspection", cascade="all, delete-orphan",
        order_by="OCRRun.created_at.desc()", lazy="selectin"
    )


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    panel_type: Mapped[PanelType] = mapped_column(
        SAEnum(PanelType, name="panel_type", native_enum=False,
               create_constraint=True, validate_strings=True),
        default=PanelType.FRONT, nullable=False
    )
    upload_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    inspection: Mapped[Inspection] = relationship("Inspection", back_populates="images")
    uploaded_by: Mapped[User] = relationship("User", foreign_keys=[uploaded_by_user_id], lazy="joined")
    processing_result: Mapped["ImageProcessingResult | None"] = relationship(
        "ImageProcessingResult", back_populates="image", uselist=False,
        cascade="all, delete-orphan", lazy="joined"
    )
    ocr_runs: Mapped[list["OCRRun"]] = relationship(
        "OCRRun", back_populates="image", cascade="all, delete-orphan",
        order_by="OCRRun.created_at.desc()", lazy="selectin"
    )
