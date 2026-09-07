from fastapi import APIRouter,Depends,Request,Query,HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.rules.engine import RuleEngine
from app.rules.schemas import EvaluateRequest

router=APIRouter(prefix="/inspections",tags=["Versioned rule evaluation"])

def engine(request:Request,db:Session=Depends(get_session)):
    return RuleEngine(db,request.app.state.settings)

@router.post("/{inspection_id}/evaluate")
def evaluate(inspection_id:str,body:EvaluateRequest | None=None,svc=Depends(engine),user:User=Depends(get_current_user)):
    return svc.evaluate(inspection_id,user,body or EvaluateRequest())

@router.get("/{inspection_id}/evaluation")
@router.get("/{inspection_id}/compliance-summary")
def summary(inspection_id:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    run=svc.get_run(inspection_id,user,run_id)
    return {**svc.summary(run),"is_current":svc.freshness(run,user)}

@router.get("/{inspection_id}/evaluation/results")
def results(inspection_id:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    return [svc.result(r) for r in svc.get_run(inspection_id,user,run_id).results]

@router.get("/{inspection_id}/evaluation/results/{result_id}")
def detail(inspection_id:str,result_id:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    run=svc.get_run(inspection_id,user,run_id)
    for row in run.results:
        if row.id==result_id: return svc.result(row)
    raise HTTPException(404,"Rule result not found")

@router.get("/{inspection_id}/rules/{rule_key}/explanation")
def explanation_by_key(inspection_id:str,rule_key:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    run=svc.get_run(inspection_id,user,run_id)
    for row in run.results:
        if row.rule_key==rule_key or row.rule_id==rule_key:
            return svc.explain(row,run,user)
    raise HTTPException(404,f"Rule result for '{rule_key}' not found in active evaluation")

@router.get("/{inspection_id}/evaluation/results/{result_id}/explanation")
def explanation_by_id(inspection_id:str,result_id:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    run=svc.get_run(inspection_id,user,run_id)
    for row in run.results:
        if row.id==result_id:
            return svc.explain(row,run,user)
    raise HTTPException(404,"Rule result not found")

@router.get("/{inspection_id}/rules/explanations")
def all_explanations(inspection_id:str,run_id:str | None=Query(None,max_length=36),svc=Depends(engine),user:User=Depends(get_current_user)):
    run=svc.get_run(inspection_id,user,run_id)
    return svc.explain_all(run,user)


