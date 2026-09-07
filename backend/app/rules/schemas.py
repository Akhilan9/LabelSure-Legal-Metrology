from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.extraction import DeclarationType

LegalStatus=Literal["VERIFIED_RULE","PROTOTYPE_RULE","LEGAL_VERIFICATION_REQUIRED","DISABLED"]
Severity=Literal["INFO","LOW","MEDIUM","HIGH","CRITICAL"]
Verdict=Literal["PASS","FAIL","UNCERTAIN","NOT_APPLICABLE"]

class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")

class EvidenceRequirements(StrictModel):
    min_confidence: float=Field(default=.85,ge=0,le=1)
    allow_absence_failure: bool=False
    required_panels: list[Literal["FRONT","BACK","LEFT","RIGHT","TOP","BOTTOM","DECLARATION_PANEL","MRP_PANEL","OTHER"]]=Field(default_factory=list,max_length=10)
    accepted_quality: list[Literal["GOOD","ACCEPTABLE"]]=Field(default_factory=lambda:["GOOD","ACCEPTABLE"],min_length=1,max_length=2)

class EvaluationConditions(StrictModel):
    validator: Literal["presence","net_quantity","month_year"]="presence"
    composition: Literal["all","any"]="all"

class RuleDefinition(StrictModel):
    rule_id: str=Field(min_length=1,max_length=64)
    rule_version: str=Field(min_length=1,max_length=32)
    rule_key: str=Field(min_length=1,max_length=64)
    title: str=Field(min_length=1,max_length=200)
    description: str=Field(min_length=1,max_length=2000)
    legal_reference: str=Field(min_length=1,max_length=500)
    legal_status: LegalStatus
    effective_from: date | None=None
    effective_to: date | None=None
    applicability_conditions: dict
    evaluation_conditions: EvaluationConditions
    required_declaration_types: list[DeclarationType]=Field(min_length=1,max_length=18)
    severity: Severity
    evidence_requirements: EvidenceRequirements
    uncertainty_behavior: Literal["UNCERTAIN"]
    enabled: bool
    verification_metadata: dict[str,str]=Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rule(self):
        from app.rules.conditions import validate_condition
        validate_condition(self.applicability_conditions)
        if self.effective_from and self.effective_to and self.effective_to<=self.effective_from:
            raise ValueError("Effective interval must be nonempty")
        if len(set(self.required_declaration_types))!=len(self.required_declaration_types):
            raise ValueError("Duplicate declaration type")
        if self.evidence_requirements.allow_absence_failure and not self.evidence_requirements.required_panels:
            raise ValueError("Absence evaluation requires explicit panel coverage")
        if self.legal_status=="VERIFIED_RULE" and not all(self.verification_metadata.get(k) for k in
            ["source","source_sha256","reviewer","verified_at"]):
            raise ValueError("Verified rules require source and reviewer metadata")
        return self

class RuleSet(StrictModel):
    ruleset_id: str=Field(min_length=1,max_length=64)
    ruleset_version: str=Field(min_length=1,max_length=32)
    description: str=Field(max_length=2000)
    rules: list[RuleDefinition]=Field(min_length=1,max_length=100)

    @model_validator(mode="after")
    def unique_rules(self):
        for key in ["rule_id","rule_key"]:
            values=[getattr(r,key) for r in self.rules]
            if len(values)!=len(set(values)):
                raise ValueError("Duplicate "+key)
        return self

class EvaluateRequest(StrictModel):
    snapshot_id: str | None=Field(default=None,max_length=36)
    allow_prototype_rules: bool=False

