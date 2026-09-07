from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, JSON, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.user import utc_now


def choice(name, *values):
    return SAEnum(*values, name=name, native_enum=False, create_constraint=True, validate_strings=True)


class InspectionReview(Base):
    __tablename__ = "inspection_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(choice("review_status", "DRAFT", "FINALIZED", "REOPENED"), default="DRAFT")
    final_compliance_status: Mapped[str | None] = mapped_column(
        choice("review_compliance_status", "COMPLIANT", "NON_COMPLIANT", "CONDITIONAL_COMPLIANCE", "REJECTED"),
        nullable=True
    )
    summary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    rule_decisions: Mapped[list["RuleReviewDecision"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RuleReviewDecision.created_at"
    )
    declaration_corrections: Mapped[list["DeclarationCorrection"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DeclarationCorrection.created_at"
    )
    ocr_corrections: Mapped[list["OCRCorrection"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OCRCorrection.created_at"
    )


class RuleReviewDecision(Base):
    __tablename__ = "rule_review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("inspection_reviews.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_key: Mapped[str] = mapped_column(String(64))
    original_verdict: Mapped[str] = mapped_column(choice("rule_review_original_verdict", "PASS", "FAIL", "UNCERTAIN", "NOT_APPLICABLE"))
    final_verdict: Mapped[str] = mapped_column(choice("rule_review_final_verdict", "PASS", "FAIL", "UNCERTAIN", "NOT_APPLICABLE"))
    is_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DeclarationCorrection(Base):
    __tablename__ = "declaration_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("inspection_reviews.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("declaration_candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    declaration_type: Mapped[str] = mapped_column(String(64))
    original_raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(choice("declaration_correction_action", "CONFIRMED", "CORRECTED", "REJECTED", "MANUALLY_ADDED"))
    correction_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OCRCorrection(Base):
    __tablename__ = "ocr_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("inspection_reviews.id", ondelete="CASCADE"), index=True)
    ocr_block_id: Mapped[str | None] = mapped_column(ForeignKey("ocr_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    inspection_image_id: Mapped[str | None] = mapped_column(ForeignKey("inspection_images.id", ondelete="SET NULL"), nullable=True, index=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(choice("ocr_correction_action", "CONFIRMED", "CORRECTED", "REJECTED", "MANUALLY_ADDED"))
    correction_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
