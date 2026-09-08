from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.context.service import ContextService,digest
from app.models.rules import RuleEvaluationRun,RuleEvaluationResult,RuleEvaluationEvidence
from app.models.user import utc_now
from app.rules.loader import load_ruleset
from app.rules.registry import RuleRegistry
from app.rules.evaluator import evaluate_rule,aggregate
from app.rules.evidence import evidence_links

class RuleEngine:
    def __init__(self,db,settings):
        self.db,self.settings=db,settings
        self.context=ContextService(db,settings)

    def configured(self):
        try: return load_ruleset(self.settings.ruleset_id,self.settings.ruleset_version)
        except (ValueError,OSError,RecursionError):
            raise HTTPException(503,"Rule configuration is invalid or unavailable")

    def evaluate(self,inspection_id,user,request):
        self.context.access(inspection_id,user,write=True)
        try: saved=self.context.snapshot(inspection_id,user,request.snapshot_id)
        except HTTPException as error:
            if error.status_code==404 and request.snapshot_id is None:
                raise HTTPException(409,"Resolve current context before rule evaluation")
            raise
        ruleset=self.configured()
        frozen=ruleset.model_dump(mode="json")
        rule_hash=digest(frozen)
        previous=self.db.scalar(select(RuleEvaluationRun).where(
            RuleEvaluationRun.ruleset_id==ruleset.ruleset_id,RuleEvaluationRun.ruleset_version==ruleset.ruleset_version))
        if previous and previous.ruleset_sha256!=rule_hash:
            raise HTTPException(409,"Ruleset content changed without a version increment")
        on_date=saved["created_at"].date()
        allow=request.allow_prototype_rules or self.settings.rules_allow_prototypes
        active,skipped=RuleRegistry(ruleset).select(on_date,allow)
        if not active:
            raise HTTPException(409,"No executable rules selected. Prototype rules require explicit opt-in; unverified/disabled rules cannot execute.")
        fingerprint=digest({"snapshot":saved["id"],"snapshot_hash":saved["content_sha256"],"ruleset_hash":rule_hash,
            "engine":self.settings.rule_engine_version,"date":on_date.isoformat(),"active":[r.rule_id for r in active]})
        cached=self.db.scalar(select(RuleEvaluationRun).where(RuleEvaluationRun.inspection_id==inspection_id,
                                                            RuleEvaluationRun.evaluation_fingerprint==fingerprint))
        if cached: return self.summary(cached)
        started=utc_now()
        outputs=[evaluate_rule(rule,saved["content"]) for rule in active]
        run=RuleEvaluationRun(inspection_id=inspection_id,rule_input_snapshot_id=saved["id"],
            snapshot_sha256=saved["content_sha256"],ruleset_id=ruleset.ruleset_id,ruleset_version=ruleset.ruleset_version,
            ruleset_sha256=rule_hash,ruleset_definition=frozen,engine_version=self.settings.rule_engine_version,
            evaluation_fingerprint=fingerprint,evaluation_date=on_date,status="SUCCESS",overall=aggregate(outputs),
            started_at=started,completed_at=utc_now(),total_rules=len(outputs),
            pass_count=sum(r["verdict"]=="PASS" for r in outputs),fail_count=sum(r["verdict"]=="FAIL" for r in outputs),
            uncertain_count=sum(r["verdict"]=="UNCERTAIN" for r in outputs),
            not_applicable_count=sum(r["verdict"]=="NOT_APPLICABLE" for r in outputs),skipped_rules=skipped)
        for output in outputs:
            row=RuleEvaluationResult(**{k:v for k,v in output.items() if k not in {"candidate_ids","context_fact_ids"}})
            row.evidence=[RuleEvaluationEvidence(**link) for link in evidence_links(output,saved["content"])]
            run.results.append(row)
        try:
            self.db.add(run); self.db.commit()
        except IntegrityError:
            self.db.rollback()
            cached=self.db.scalar(select(RuleEvaluationRun).where(RuleEvaluationRun.inspection_id==inspection_id,
                                                                 RuleEvaluationRun.evaluation_fingerprint==fingerprint))
            if cached: return self.summary(cached)
            raise
        return self.summary(run)

    def get_run(self,inspection_id,user,run_id=None):
        self.context.access(inspection_id,user)
        query=select(RuleEvaluationRun).where(RuleEvaluationRun.inspection_id==inspection_id)
        if run_id: query=query.where(RuleEvaluationRun.id==run_id)
        run=self.db.scalar(query.order_by(RuleEvaluationRun.created_at.desc(),RuleEvaluationRun.id.desc()))
        if run is None: raise HTTPException(404,"Evaluation not found")
        return run

    def summary(self,run):
        from app.rules.justifications import generate_failure_justifications
        failed_rules = [r for r in run.results if r.verdict == "FAIL"]
        failure_justifications = generate_failure_justifications(failed_rules)
        return {**{k:getattr(run,k) for k in ["id","inspection_id","rule_input_snapshot_id","snapshot_sha256",
            "ruleset_id","ruleset_version","ruleset_sha256","engine_version","evaluation_date","status","overall",
            "started_at","completed_at","total_rules","pass_count","fail_count","uncertain_count","not_applicable_count","skipped_rules"]},
            "prototype": any(r.legal_status == "PROTOTYPE_RULE" for r in run.results) or run.ruleset_id == "labelsure_prototype",
            "guideline_failure_justifications": failure_justifications,
            "scope":"Preliminary result within the selected ruleset; human inspector review required."}

    def result(self,row):
        return {**{c.name:getattr(row,c.name) for c in RuleEvaluationResult.__table__.columns},
            "evidence":[{c.name:getattr(e,c.name) for c in RuleEvaluationEvidence.__table__.columns} for e in row.evidence]}

    def freshness(self,run,user):
        try:
            snapshot=self.context.snapshot(run.inspection_id,user)
            return snapshot["id"]==run.rule_input_snapshot_id and run.engine_version==self.settings.rule_engine_version and run.ruleset_id==self.settings.ruleset_id and run.ruleset_version==self.settings.ruleset_version and digest(self.configured().model_dump(mode="json"))==run.ruleset_sha256
        except HTTPException: return False

    def explain(self, row, run, user):
        snapshot = self.context.snapshot(run.inspection_id, user, run.rule_input_snapshot_id)
        from app.rules.explainability import explain_result
        return explain_result(self.result(row), self.summary(run), snapshot["content"])

    def explain_all(self, run, user):
        snapshot = self.context.snapshot(run.inspection_id, user, run.rule_input_snapshot_id)
        from app.rules.explainability import explain_result
        summary_data = self.summary(run)
        return [explain_result(self.result(r), summary_data, snapshot["content"]) for r in run.results]


