from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.context.service import ContextService
from app.context.schemas import ResolveRequest

router=APIRouter(prefix="/inspections",tags=["Context and applicability preparation"])

def service(request:Request,db:Session=Depends(get_session)):
    return ContextService(db,request.app.state.settings)

@router.post("/{inspection_id}/resolve-context")
def resolve_context(inspection_id:str,body:ResolveRequest | None=None,svc=Depends(service),user:User=Depends(get_current_user)):
    update=body.inspector_input.model_dump(exclude_unset=True) if body and body.inspector_input else None
    return svc.run(inspection_id,user,update)

@router.get("/{inspection_id}/context")
def context(inspection_id:str,svc=Depends(service),user:User=Depends(get_current_user)):
    return svc.context(svc.current(inspection_id,user))

@router.get("/{inspection_id}/context/facts")
def facts(inspection_id:str,svc=Depends(service),user:User=Depends(get_current_user)):
    # Return immutable snapshot fact records, scoped to current evidence.
    run=svc.current(inspection_id,user)
    return svc.snapshot(inspection_id,user)["content"]["facts"] if run else []

@router.get("/{inspection_id}/rule-input")
def rule_input(inspection_id:str,snapshot_id:str | None=Query(None,max_length=36),svc=Depends(service),user:User=Depends(get_current_user)):
    return svc.snapshot(inspection_id,user,snapshot_id)

@router.get("/{inspection_id}/applicability-preview")
def applicability(inspection_id:str,svc=Depends(service),user:User=Depends(get_current_user)):
    snapshot=svc.snapshot(inspection_id,user)
    return {"snapshot_id":snapshot["id"],"verification_status":"TODO_LEGAL_VERIFICATION",
            "items":snapshot["content"]["applicability_preview"],"message":"Preparation only; no legal rules are executed."}

