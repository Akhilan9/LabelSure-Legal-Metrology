from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import String, JSON, Float, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.extraction import enum_column
from app.models.user import utc_now

class ResolutionState(str, Enum):
    KNOWN = "KNOWN"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class SourceType(str, Enum):
    INSPECTOR_INPUT = "INSPECTOR_INPUT"
    INSPECTION_METADATA = "INSPECTION_METADATA"
    DECLARATION_CANDIDATE = "DECLARATION_CANDIDATE"
    OCR_EVIDENCE = "OCR_EVIDENCE"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

class FactType(str, Enum):
    PRODUCT_CATEGORY = "PRODUCT_CATEGORY"
    PACKAGE_TYPE = "PACKAGE_TYPE"
    IMPORT_STATUS = "IMPORT_STATUS"
    COUNTRY_OF_ORIGIN = "COUNTRY_OF_ORIGIN"
    QUANTITY_KIND = "QUANTITY_KIND"
    HAS_MRP_CANDIDATE = "HAS_MRP_CANDIDATE"
    HAS_NET_QUANTITY_CANDIDATE = "HAS_NET_QUANTITY_CANDIDATE"
    HAS_MANUFACTURER_CANDIDATE = "HAS_MANUFACTURER_CANDIDATE"
    HAS_PACKER_CANDIDATE = "HAS_PACKER_CANDIDATE"
    HAS_IMPORTER_CANDIDATE = "HAS_IMPORTER_CANDIDATE"
    HAS_CONSUMER_CARE_CANDIDATE = "HAS_CONSUMER_CARE_CANDIDATE"
    HAS_MONTH_YEAR_CANDIDATE = "HAS_MONTH_YEAR_CANDIDATE"
    HAS_COMMON_NAME_CANDIDATE = "HAS_COMMON_NAME_CANDIDATE"
    HAS_COUNTRY_OF_ORIGIN_CANDIDATE = "HAS_COUNTRY_OF_ORIGIN_CANDIDATE"
    OCR_EVIDENCE_AVAILABLE = "OCR_EVIDENCE_AVAILABLE"
    OCR_CONFIDENCE_STATE = "OCR_CONFIDENCE_STATE"
    DECLARATION_CONFLICT_PRESENT = "DECLARATION_CONFLICT_PRESENT"

class EvidenceSufficiency(str, Enum):
    SUFFICIENT_FOR_RULE_EVALUATION = "SUFFICIENT_FOR_RULE_EVALUATION"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class ContextRunStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class ContextResolutionRun(Base):
    __tablename__ = "context_resolution_runs"
    __table_args__ = (UniqueConstraint("inspection_id","version","input_fingerprint",name="uq_context_input"),)
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id",ondelete="CASCADE"),index=True)
    version: Mapped[str] = mapped_column(String(32))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)
    inspector_input: Mapped[dict] = mapped_column(JSON)
    status: Mapped[ContextRunStatus] = mapped_column(enum_column(ContextRunStatus,"context_run_status"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    facts_created: Mapped[int] = mapped_column(Integer,default=0)
    conflicts_detected: Mapped[int] = mapped_column(Integer,default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)

class InspectionContext(Base):
    __tablename__ = "inspection_contexts"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id",ondelete="CASCADE"),index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("context_resolution_runs.id",ondelete="CASCADE"),unique=True)
    context_version: Mapped[str] = mapped_column(String(32))
    resolved: Mapped[dict] = mapped_column(JSON)
    resolution_status: Mapped[ResolutionState] = mapped_column(enum_column(ResolutionState,"context_resolution_state"))
    evidence: Mapped[dict] = mapped_column(JSON)
    conflicts: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)

class ContextFact(Base):
    __tablename__ = "context_facts"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id",ondelete="CASCADE"),index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("context_resolution_runs.id",ondelete="CASCADE"),index=True)
    fact_type: Mapped[FactType] = mapped_column(enum_column(FactType,"context_fact_type"))
    value: Mapped[dict] = mapped_column(JSON)
    source_type: Mapped[SourceType] = mapped_column(enum_column(SourceType,"context_source_type"))
    source_reference_id: Mapped[str | None] = mapped_column(String(36))
    confidence: Mapped[float | None] = mapped_column(Float)
    resolution_state: Mapped[ResolutionState] = mapped_column(enum_column(ResolutionState,"fact_resolution_state"))
    explanation: Mapped[str] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)

class RuleInputSnapshot(Base):
    __tablename__ = "rule_input_snapshots"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id",ondelete="CASCADE"),index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("context_resolution_runs.id",ondelete="CASCADE"),unique=True)
    schema_version: Mapped[str] = mapped_column(String(32),default="1")
    content: Mapped[dict] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utc_now)

@event.listens_for(RuleInputSnapshot, "before_update")
def immutable_snapshot(mapper, connection, target):
    raise ValueError("Rule input snapshots are immutable; create a new context resolution")

