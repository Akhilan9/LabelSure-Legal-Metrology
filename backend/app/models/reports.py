from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, JSON, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.user import utc_now


def choice(name, *values):
    return SAEnum(*values, name=name, native_enum=False, create_constraint=True, validate_strings=True)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    report_type: Mapped[str] = mapped_column(
        choice("report_type", "SUMMARY", "DETAILED", "LEGAL_NOTICE", "VIOLATION_EXPORT"),
        default="SUMMARY"
    )
    format: Mapped[str] = mapped_column(
        choice("report_format", "PDF", "JSON", "CSV"),
        default="PDF"
    )
    status: Mapped[str] = mapped_column(
        choice("report_status", "GENERATED", "FAILED"),
        default="GENERATED"
    )
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    report_data: Mapped[dict] = mapped_column(JSON, default=dict)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
