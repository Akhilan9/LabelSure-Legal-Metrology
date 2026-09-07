from datetime import datetime,date
from uuid import uuid4
from sqlalchemy import String,JSON,Float,Integer,Date,DateTime,ForeignKey,UniqueConstraint,Enum as SAEnum
from sqlalchemy.orm import Mapped,mapped_column,relationship
from app.db.session import Base
from app.models.user import utc_now

def choice(name,*values):
    return SAEnum(*values,name=name,native_enum=False,create_constraint=True,validate_strings=True)

class RuleEvaluationRun(Base):
    __tablename__="rule_evaluation_runs"
    __table_args__=(UniqueConstraint("inspection_id","evaluation_fingerprint",name="uq_rule_evaluation_input"),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    inspection_id: Mapped[str]=mapped_column(ForeignKey("inspections.id",ondelete="CASCADE"),index=True)
    rule_input_snapshot_id: Mapped[str]=mapped_column(ForeignKey("rule_input_snapshots.id",ondelete="RESTRICT"),index=True)
    snapshot_sha256: Mapped[str]=mapped_column(String(64))
    ruleset_id: Mapped[str]=mapped_column(String(64))
    ruleset_version: Mapped[str]=mapped_column(String(32))
    ruleset_sha256: Mapped[str]=mapped_column(String(64))
    ruleset_definition: Mapped[dict]=mapped_column(JSON)
    engine_version: Mapped[str]=mapped_column(String(32))
    evaluation_fingerprint: Mapped[str]=mapped_column(String(64))
    evaluation_date: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(choice("rule_run_status","SUCCESS","FAILED"))
    overall: Mapped[str]=mapped_column(choice("rule_overall","PASS","FAIL","UNCERTAIN"))
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    total_rules: Mapped[int]=mapped_column(Integer)
    pass_count: Mapped[int]=mapped_column(Integer)
    fail_count: Mapped[int]=mapped_column(Integer)
    uncertain_count: Mapped[int]=mapped_column(Integer)
    not_applicable_count: Mapped[int]=mapped_column(Integer)
    skipped_rules: Mapped[list]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    results: Mapped[list["RuleEvaluationResult"]]=relationship(cascade="all, delete-orphan",lazy="selectin",order_by="RuleEvaluationResult.rule_id")

class RuleEvaluationResult(Base):
    __tablename__="rule_evaluation_results"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    evaluation_run_id: Mapped[str]=mapped_column(ForeignKey("rule_evaluation_runs.id",ondelete="CASCADE"),index=True)
    rule_id: Mapped[str]=mapped_column(String(64))
    rule_key: Mapped[str]=mapped_column(String(64))
    rule_version: Mapped[str]=mapped_column(String(32))
    title: Mapped[str]=mapped_column(String(200))
    verdict: Mapped[str]=mapped_column(choice("rule_verdict","PASS","FAIL","UNCERTAIN","NOT_APPLICABLE"))
    severity: Mapped[str]=mapped_column(choice("rule_severity","INFO","LOW","MEDIUM","HIGH","CRITICAL"))
    reason_code: Mapped[str]=mapped_column(String(64))
    explanation: Mapped[str]=mapped_column(String(2000))
    legal_reference: Mapped[str]=mapped_column(String(500))
    legal_status: Mapped[str]=mapped_column(choice("rule_legal_status","VERIFIED_RULE","PROTOTYPE_RULE","LEGAL_VERIFICATION_REQUIRED","DISABLED"))
    applicability_state: Mapped[str]=mapped_column(choice("rule_applicability_state","APPLICABLE","NOT_APPLICABLE","UNKNOWN"))
    evidence_confidence: Mapped[float | None]=mapped_column(Float)
    rule_definition: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    evidence: Mapped[list["RuleEvaluationEvidence"]]=relationship(cascade="all, delete-orphan",lazy="selectin",order_by="RuleEvaluationEvidence.id")

class RuleEvaluationEvidence(Base):
    __tablename__="rule_evaluation_evidence"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    result_id: Mapped[str]=mapped_column(ForeignKey("rule_evaluation_results.id",ondelete="CASCADE"),index=True)
    evidence_type: Mapped[str]=mapped_column(choice("rule_evidence_type","DECLARATION","OCR_BLOCK","IMAGE","CONTEXT_FACT","COVERAGE"))
    declaration_candidate_id: Mapped[str | None]=mapped_column(String(36))
    ocr_block_id: Mapped[str | None]=mapped_column(String(36))
    inspection_image_id: Mapped[str | None]=mapped_column(String(36))
    context_fact_id: Mapped[str | None]=mapped_column(String(36))
    evidence_role: Mapped[str]=mapped_column(choice("rule_evidence_role","SUPPORTING","CONTRADICTING","MISSING_EXPECTED","CONTEXT"))
    detail: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)

