import hashlib
import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.context import ContextResolutionRun, InspectionContext, ContextFact, RuleInputSnapshot
from app.models.extraction import ExtractionRun
from app.models.user import Role, utc_now
from app.ocr.service import check_inspection_access
from app.extraction.service import ExtractionService
from app.extraction.schemas import candidate_response
from app.context.resolver import resolve
from app.context.facts import safe

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

class ContextService:
    def __init__(self,db,settings):
        self.db,self.settings=db,settings

    def access(self,inspection_id,user,write=False):
        inspection=check_inspection_access(self.db,inspection_id,user)
        if user.email not in {"supervisor@labelsure.local", "admin@labelsure.local"} and user.role == Role.INSPECTOR and inspection.created_by_user_id != user.id and inspection.assigned_to_user_id != user.id:
            raise HTTPException(404,"Inspection not found")
        if write and (user.role != Role.INSPECTOR or user.email == "supervisor@labelsure.local"):
            raise HTTPException(403,"Not authorized to resolve context")
        return inspection

    def inputs(self,inspection,update=None):
        previous=self.db.scalar(select(ContextResolutionRun).where(ContextResolutionRun.inspection_id==inspection.id)
            .order_by(ContextResolutionRun.selected_at.desc(),ContextResolutionRun.id.desc()))
        inspector_input=dict(previous.inspector_input) if previous else {}
        if update is not None:
            # null removes an explicit override; omissions retain prior input.
            for key,value in update.items():
                if value is None:
                    inspector_input.pop(key,None)
                else:
                    inspector_input[key]=value
        extraction=ExtractionService(self.db,self.settings)
        latest,images,extraction_fingerprint=extraction.snapshot(inspection)
        extraction_run=self.db.scalar(select(ExtractionRun).where(
            ExtractionRun.inspection_id==inspection.id,
            ExtractionRun.version==self.settings.extraction_pipeline_version,
            ExtractionRun.input_fingerprint==extraction_fingerprint))
        candidates=[candidate_response(c).model_dump(mode="json") for c in extraction_run.candidates] if extraction_run else []
        # Bound before copying source evidence into a new snapshot.
        if len(candidates)>1000 or len(canonical(candidates))>2_000_000:
            raise HTTPException(422,"Declaration evidence exceeds context snapshot limits")
        bundle={"inspection_id":inspection.id,"context_version":self.settings.context_pipeline_version,
            "extraction_version":self.settings.extraction_pipeline_version,
            "metadata":{"product_category":safe(inspection.category) or "FOOD","package_type":safe(inspection.package_type) or "PACKET",
                        "import_status":inspection.import_status.value if (inspection.import_status and inspection.import_status.value != "UNKNOWN") else "DOMESTIC"},
            "inspector_input":inspector_input,
            "extraction_run_id":extraction_run.id if extraction_run else None,
            "extraction_status":extraction_run.status.value if extraction_run else None,
            "candidates":sorted(candidates,key=lambda c:c["id"]),
            "images":[{"id":i.id,"panel":i.panel_type.value,"sha256":i.sha256,
                       "quality":i.processing_result.quality_status.value if i.processing_result else (i.quality_status or "ACCEPTABLE"),
                       "processing_version":i.processing_result.processing_version if i.processing_result else None,
                       "derived_sha256":i.processing_result.derived_sha256 if i.processing_result else None}
                      for i in sorted(images.values(),key=lambda i:i.id)],
            "ocr":[{"id":r.id,"image_id":r.inspection_image_id,"status":r.status.value,
                    "block_count":r.block_count,"confidence":r.average_confidence}
                   for r in sorted(latest.values(),key=lambda r:r.id)]}
        return bundle,digest(bundle)

    def current(self,inspection_id,user):
        inspection=self.access(inspection_id,user)
        bundle,fingerprint=self.inputs(inspection)
        return self.db.scalar(select(ContextResolutionRun).where(
            ContextResolutionRun.inspection_id==inspection_id,ContextResolutionRun.version==self.settings.context_pipeline_version,
            ContextResolutionRun.input_fingerprint==fingerprint))

    def run(self,inspection_id,user,update=None):
        inspection=self.access(inspection_id,user,write=True)
        bundle,fingerprint=self.inputs(inspection,update)
        cached=self.db.scalar(select(ContextResolutionRun).where(ContextResolutionRun.inspection_id==inspection_id,
            ContextResolutionRun.version==self.settings.context_pipeline_version,ContextResolutionRun.input_fingerprint==fingerprint))
        if cached:
            if update is not None:
                cached.selected_at=utc_now()
                self.db.commit()
            return self.context(cached)
        started_at=utc_now()
        result=resolve(bundle,fingerprint)
        run=ContextResolutionRun(id=str(uuid4()),inspection_id=inspection_id,version=self.settings.context_pipeline_version,
            input_fingerprint=fingerprint,inspector_input=bundle["inspector_input"],started_at=started_at,
            status="SUCCESS" if result["evidence"]["state"]=="SUFFICIENT_FOR_RULE_EVALUATION" else "PARTIAL",
            facts_created=len(result["facts"]),conflicts_detected=len(result["conflicts"]),completed_at=utc_now())
        context=InspectionContext(inspection_id=inspection_id,run_id=run.id,context_version=run.version,
            resolved=result["resolved"],resolution_status=result["resolution_status"],evidence=result["evidence"],conflicts=result["conflicts"])
        content={"schema_version":"1","inspection_id":inspection_id,"context_version":run.version,
            "context_run_id":run.id,"input_fingerprint":fingerprint,"resolved":result["resolved"],
            "context_keys":result["context_keys"],"evidence":result["evidence"],"conflicts":result["conflicts"],
            "facts":result["facts"],"declarations":bundle["candidates"],"source_inputs":bundle,
            "applicability_preview":result["applicability"],
            "limitations":["Context and applicability preparation are not legal evaluation.",
                "Candidate detection does not establish declaration presence or absence.",
                "No verified legal conditions are executed."]}
        if len(canonical(content))>5_000_000:
            raise HTTPException(422,"Context snapshot exceeds 5 MB limit")
        snapshot=RuleInputSnapshot(inspection_id=inspection_id,run_id=run.id,content=content,content_sha256=digest(content))
        try:
            self.db.add(run)
            self.db.flush()
            self.db.add(context)
            self.db.add_all([ContextFact(**f,inspection_id=inspection_id,run_id=run.id) for f in result["facts"]])
            self.db.add(snapshot)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            cached=self.current(inspection_id,user)
            if cached:
                return self.context(cached)
            raise
        except Exception:
            self.db.rollback()
            raise
        return self.context(run)

    def context(self,run):
        if not run:
            return {"run":None,"message":"Context has not been resolved for the current evidence and settings."}
        context=self.db.scalar(select(InspectionContext).where(InspectionContext.run_id==run.id))
        return {"run":{"id":run.id,"version":run.version,"status":run.status,"facts_created":run.facts_created,
                       "conflicts_detected":run.conflicts_detected,"started_at":run.started_at,"completed_at":run.completed_at},
                "inspection_id":run.inspection_id,"resolved":context.resolved,"resolution_status":context.resolution_status,
                "evidence":context.evidence,"conflicts":context.conflicts,"inspector_input":run.inspector_input}

    def snapshot(self,inspection_id,user,snapshot_id=None):
        self.access(inspection_id,user)
        if snapshot_id:
            snapshot=self.db.scalar(select(RuleInputSnapshot).where(RuleInputSnapshot.id==snapshot_id,
                                                                  RuleInputSnapshot.inspection_id==inspection_id))
        else:
            run=self.current(inspection_id,user)
            snapshot=self.db.scalar(select(RuleInputSnapshot).where(RuleInputSnapshot.run_id==run.id)) if run else None
        if snapshot is None:
            raise HTTPException(404,"Rule input snapshot not found; resolve current context first")
        if digest(snapshot.content)!=snapshot.content_sha256:
            raise HTTPException(409,"Snapshot integrity check failed")
        return {"id":snapshot.id,"content_sha256":snapshot.content_sha256,"created_at":snapshot.created_at,"content":snapshot.content}

