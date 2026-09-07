import copy
import json
import time
import pytest
from sqlalchemy import select, func, text
from test_ocr import client, auth_headers
from test_extraction import prepare, SYNTHETIC
from app.context.resolver import resolve
from app.context.service import digest
from app.context.facts import quantity_kind
from app.models.context import ContextFact, ContextResolutionRun, RuleInputSnapshot
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.service import set_custom_ocr_provider

def bundle():
    return {"inspection_id":"i","context_version":"1","extraction_version":"1",
        "metadata":{"product_category":"Food","package_type":"Pouch","import_status":"UNKNOWN"},
        "inspector_input":{},"extraction_run_id":"e","extraction_status":"SUCCESS","candidates":[],
        "images":[{"id":"im","panel":"FRONT","quality":"GOOD"}],
        "ocr":[{"id":"o","image_id":"im","status":"SUCCESS","block_count":5,"confidence":.98}]}

def candidate(kind,value,unit=None,confidence=.95,review=False):
    return {"id":kind+value,"declaration_type":kind,"normalized_value":value,"raw_value":value,
        "structured_value":{"unit":unit},"confidence_score":confidence,"needs_review":review,
        "review_reasons":[],"sources":[{"ocr_block_id":"b"}]}

def result(data):
    return resolve(data,digest(data))

def test_metadata_normalization_and_null_confidence():
    data=bundle()
    data["metadata"]["import_status"]="DOMESTIC"
    r=result(data)
    assert r["resolved"]["PRODUCT_CATEGORY"]["value"]=="FOOD"
    assert r["resolved"]["PACKAGE_TYPE"]["value"]=="POUCH"
    assert r["resolved"]["IMPORT_STATUS"]["state"]=="KNOWN"
    assert r["resolved"]["IMPORT_STATUS"]["confidence"] is None
    assert next(f for f in r["facts"] if f["fact_type"]=="PACKAGE_TYPE")["value"]["raw"]=="Pouch"

@pytest.mark.parametrize("unit,expected",[("g","WEIGHT"),("kg","WEIGHT"),("ml","VOLUME"),("L","VOLUME"),
    ("pieces","COUNT"),("count","COUNT"),("m","LENGTH"),("m2","AREA"),("?","UNKNOWN"),(None,"UNKNOWN")])
def test_quantity_resolution(unit,expected):
    data=bundle()
    data["candidates"]=[candidate("NET_QUANTITY","500 "+str(unit),unit)]
    r=result(data)
    assert r["resolved"]["QUANTITY_KIND"]["value"]==expected
    assert quantity_kind(unit)==expected

def test_foreign_origin_never_automatically_imported():
    data=bundle()
    data["candidates"]=[candidate("COUNTRY_OF_ORIGIN","Germany")]
    r=result(data)
    assert r["resolved"]["COUNTRY_OF_ORIGIN"]["value"]=="Germany"
    assert r["resolved"]["IMPORT_STATUS"]["value"]=="UNKNOWN"
    assert r["resolved"]["COUNTRY_OF_ORIGIN"]["source_type"]=="DECLARATION_CANDIDATE"

def test_importer_signal_requires_review():
    data=bundle()
    data["candidates"]=[candidate("IMPORTER_NAME","Imported by ABC Ltd")]
    r=result(data)
    assert r["resolved"]["IMPORT_STATUS"]["state"]=="REVIEW_REQUIRED"
    importer=next(p for p in r["applicability"] if p["rule_key"]=="DECLARATION_IMPORTER")
    assert importer["state"]=="APPLICABILITY_UNCERTAIN"
    assert importer["executable"] is False

def test_source_priority_preserves_disagreement():
    data=bundle()
    data["metadata"]["import_status"]="DOMESTIC"
    data["inspector_input"]["import_status"]="IMPORTED"
    r=result(data)
    assert r["resolved"]["IMPORT_STATUS"]["value"]=="IMPORTED"
    assert r["resolved"]["IMPORT_STATUS"]["state"]=="CONFLICTING"
    assert len(r["conflicts"][0]["sources"])==2
    assert len(r["resolved"]["IMPORT_STATUS"]["fact_ids"])==2

def test_domestic_vs_importer_conflict():
    data=bundle()
    data["metadata"]["import_status"]="DOMESTIC"
    data["candidates"]=[candidate("IMPORTER_NAME","Imported by ABC India",confidence=.789,review=True)]
    r=result(data)
    assert r["resolved"]["IMPORT_STATUS"]["value"]=="DOMESTIC"
    assert r["resolved"]["IMPORT_STATUS"]["state"]=="CONFLICTING"
    assert r["evidence"]["state"]=="REVIEW_REQUIRED"

@pytest.mark.parametrize("status,expected",[("DOMESTIC","NOT_APPLICABLE_BY_CONTEXT"),
    ("IMPORTED","POTENTIALLY_APPLICABLE"),("UNKNOWN","APPLICABILITY_UNCERTAIN")])
def test_import_preview_unverified(status,expected):
    data=bundle()
    data["inspector_input"]["import_status"]=status
    r=result(data)
    p=next(p for p in r["applicability"] if p["rule_key"]=="DECLARATION_IMPORTER")
    assert p["state"]==expected
    assert p["verification_status"]=="TODO_LEGAL_VERIFICATION"
    assert all(not p["executable"] for p in r["applicability"])

@pytest.mark.parametrize("declaration,fact",[
    ("MRP","HAS_MRP_CANDIDATE"),("NET_QUANTITY","HAS_NET_QUANTITY_CANDIDATE"),
    ("MANUFACTURER_NAME","HAS_MANUFACTURER_CANDIDATE"),("PACKER_ADDRESS","HAS_PACKER_CANDIDATE"),
    ("IMPORTER_NAME","HAS_IMPORTER_CANDIDATE"),("CONSUMER_CARE_PHONE","HAS_CONSUMER_CARE_CANDIDATE"),
    ("MONTH_YEAR","HAS_MONTH_YEAR_CANDIDATE"),("COMMON_PRODUCT_NAME","HAS_COMMON_NAME_CANDIDATE"),
    ("COUNTRY_OF_ORIGIN","HAS_COUNTRY_OF_ORIGIN_CANDIDATE")])
def test_detection_facts_and_provenance(declaration,fact):
    data=bundle()
    c=candidate(declaration,"value")
    data["candidates"]=[c]
    r=result(data)
    assert r["resolved"][fact]["value"] is True
    f=next(f for f in r["facts"] if f["fact_type"]==fact)
    assert f["value"]["references"]==[c["id"]]

def test_no_extraction_presence_is_unknown():
    data=bundle()
    data["extraction_run_id"]=None
    data["extraction_status"]=None
    r=result(data)
    assert r["resolved"]["HAS_MRP_CANDIDATE"]["value"] is None
    assert r["evidence"]["state"]=="PARTIAL"

def test_failed_ocr_is_insufficient_not_verdict():
    data=bundle()
    data["ocr"][0]["status"]="FAILED"
    r=result(data)
    assert r["evidence"]["state"]=="INSUFFICIENT"
    assert r["resolved"]["OCR_EVIDENCE_AVAILABLE"]["value"] is False
    assert_no_verdict(r)

def test_low_confidence_no_mrp_is_not_legal_absence():
    data=bundle()
    data["ocr"][0]["confidence"]=.4
    r=result(data)
    assert r["resolved"]["HAS_MRP_CANDIDATE"]["value"] is False
    assert r["evidence"]["state"]=="REVIEW_REQUIRED"
    assert_no_verdict(r)

@pytest.mark.parametrize("quality,expected",[("GOOD","SUFFICIENT_FOR_RULE_EVALUATION"),
    ("ACCEPTABLE","SUFFICIENT_FOR_RULE_EVALUATION"),("POOR","REVIEW_REQUIRED"),
    ("UNREADABLE","INSUFFICIENT"),("PROCESSING_FAILED","INSUFFICIENT"),(None,"PARTIAL")])
def test_quality_sufficiency(quality,expected):
    data=bundle()
    data["images"][0]["quality"]=quality
    assert result(data)["evidence"]["state"]==expected

def assert_no_verdict(data):
    forbidden={"PASS","FAIL","COMPLIANT","NON_COMPLIANT"}
    def walk(value):
        if isinstance(value,dict):
            assert not forbidden.intersection(value.keys())
            for v in value.values(): walk(v)
        elif isinstance(value,list):
            for v in value: walk(v)
        elif isinstance(value,str):
            assert value not in forbidden
    walk(data)

def test_context_keys_keep_resolution_states():
    data=bundle()
    data["metadata"]["import_status"]="DOMESTIC"
    data["candidates"]=[candidate("IMPORTER_NAME","Importer")]
    r=result(data)
    assert r["context_keys"]["package.import_status"]["state"]=="CONFLICTING"
    assert r["context_keys"]["declaration.mrp.detected"]["value"] is False
    assert "evidence.sufficiency" in r["context_keys"]

def test_deterministic_resolution_and_runtime():
    data=bundle()
    before=copy.deepcopy(data)
    started=time.perf_counter()
    r=result(data)
    assert result(data)==r
    assert data==before
    assert time.perf_counter()-started<1

def test_context_api_end_to_end(client):
    base,headers,_=prepare(client,SYNTHETIC)
    client.post(base+"/extract-declarations",headers=headers).raise_for_status()
    r=client.post(base+"/resolve-context",json={"inspector_input":{"import_status":"DOMESTIC","package_type":"POUCH","product_category":"FOOD"}},headers=headers)
    assert r.status_code==200,r.text
    assert r.json()["run"]["started_at"] <= r.json()["run"]["completed_at"]
    assert r.json()["resolved"]["QUANTITY_KIND"]["value"]=="WEIGHT"
    assert r.json()["resolved"]["IMPORT_STATUS"]["state"]=="KNOWN"
    snapshot=client.get(base+"/rule-input",headers=headers).json()
    assert digest(snapshot["content"])==snapshot["content_sha256"]
    assert snapshot["content"]["declarations"]
    assert snapshot["content"]["facts"]
    assert_no_verdict(snapshot)
    assert client.post(base+"/resolve-context",headers=headers).json()["run"]["id"]==r.json()["run"]["id"]
    assert client.get(base+"/rule-input",headers=headers).json()==snapshot
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ContextResolutionRun))==1
        assert db.scalar(select(func.count()).select_from(ContextFact))==r.json()["run"]["facts_created"]

def test_metadata_only_context(client):
    base,headers,_=prepare(client)
    r=client.post(base+"/resolve-context",headers=headers)
    assert r.status_code==200,r.text
    assert r.json()["evidence"]["state"]=="INSUFFICIENT"
    assert r.json()["resolved"]["HAS_MRP_CANDIDATE"]["value"] is None

def test_snapshot_history_and_version(client):
    base,headers,_=prepare(client,["MRP 120"])
    client.post(base+"/extract-declarations",headers=headers)
    client.post(base+"/resolve-context",headers=headers)
    old=client.get(base+"/rule-input",headers=headers).json()
    client.app.state.settings.context_pipeline_version="2"
    assert client.get(base+"/context",headers=headers).json()["run"] is None
    client.post(base+"/resolve-context",headers=headers)
    new=client.get(base+"/rule-input",headers=headers).json()
    assert old["id"]!=new["id"]
    assert client.get(base+"/rule-input?snapshot_id="+old["id"],headers=headers).json()==old

def test_cached_input_reactivation_and_clearing(client):
    base,headers,_=prepare(client)
    def run(value):
        return client.post(base+"/resolve-context",json={"inspector_input":{"import_status":value}},headers=headers).json()
    first=run("IMPORTED")
    run("DOMESTIC")
    assert run("IMPORTED")["run"]["id"]==first["run"]["id"]
    assert client.get(base+"/context",headers=headers).json()["resolved"]["IMPORT_STATUS"]["value"]=="IMPORTED"
    cleared=run(None)
    assert cleared["resolved"]["IMPORT_STATUS"]["value"]=="UNKNOWN"

def test_ocr_change_invalidates_current_snapshot(client):
    base,headers,image=prepare(client,["MRP 120"])
    client.post(base+"/extract-declarations",headers=headers)
    client.post(base+"/resolve-context",headers=headers)
    old=client.get(base+"/rule-input",headers=headers).json()
    set_custom_ocr_provider(MockOCRProvider(simulate_failure=True))
    client.post(base+"/images/"+image+"/ocr?force=true",headers=headers)
    assert client.get(base+"/context",headers=headers).json()["run"] is None
    r=client.post(base+"/resolve-context",headers=headers).json()
    assert r["evidence"]["state"]=="INSUFFICIENT"
    assert r["resolved"]["HAS_MRP_CANDIDATE"]["value"] is None
    assert client.get(base+"/rule-input?snapshot_id="+old["id"],headers=headers).json()==old

def test_context_rbac_and_idor(client):
    base,headers,_=prepare(client)
    admin=auth_headers(client,"admin@labelsure.local")
    other=auth_headers(client,"inspector2@labelsure.local")
    supervisor=auth_headers(client,"supervisor@labelsure.local")
    assert client.post(base+"/resolve-context",headers=admin).status_code==200
    for suffix in ["/context","/context/facts","/rule-input","/applicability-preview"]:
        assert client.get(base+suffix).status_code==401
        assert client.get(base+suffix,headers=other).status_code==404
        assert client.get(base+suffix,headers=supervisor).status_code==200
    assert client.post(base+"/resolve-context",headers=other).status_code==404
    assert client.post(base+"/resolve-context",headers=supervisor).status_code==403
    assert client.post(base+"/resolve-context").status_code==401
    snapshot=client.get(base+"/rule-input",headers=headers).json()
    other_base,_,_=prepare(client)
    assert client.get(other_base+"/rule-input?snapshot_id="+snapshot["id"],headers=headers).status_code==404

@pytest.mark.parametrize("payload",[
    {"rule_key":"arbitrary"},
    {"inspector_input":{"internal.rule":True}},
    {"inspector_input":{"country_of_origin":"x"*101}},
    {"inspector_input":{"country_of_origin":"bad\u0000text"}},
    {"inspector_input":{"import_status":"COMPLIANT"}},
])
def test_reject_untrusted_input(client,payload):
    base,headers,_=prepare(client)
    assert client.post(base+"/resolve-context",json=payload,headers=headers).status_code==422

def test_snapshot_tampering_protection(client):
    base,headers,_=prepare(client)
    client.post(base+"/resolve-context",headers=headers)
    saved=client.get(base+"/rule-input",headers=headers).json()
    with client.app.state.session_factory() as db:
        snapshot=db.get(RuleInputSnapshot,saved["id"])
        snapshot.content={"modified":True}
        with pytest.raises(ValueError,match="immutable"):
            db.commit()
        db.rollback()
        # Simulate direct database corruption; API integrity check must detect it.
        db.execute(text("UPDATE rule_input_snapshots SET content='{}' WHERE id=:id"),{"id":saved["id"]})
        db.commit()
    assert client.get(base+"/rule-input",headers=headers).status_code==409
    assert client.put(base+"/rule-input",json={"content":{}},headers=headers).status_code==405

def test_snapshot_excludes_internal_secrets_and_paths(client):
    base,headers,_=prepare(client)
    client.post(base+"/resolve-context",headers=headers)
    content=client.get(base+"/rule-input",headers=headers).text
    assert all(key not in content for key in ["storage_path","hashed_password","JWT_SECRET","Authorization","access_token"])

def test_inspection_status_unchanged(client):
    base,headers,_=prepare(client)
    old=client.get(base,headers=headers).json()["status"]
    client.post(base+"/resolve-context",headers=headers)
    assert client.get(base,headers=headers).json()["status"]==old

