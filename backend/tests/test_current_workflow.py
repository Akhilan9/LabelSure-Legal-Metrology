import secrets
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import Base
from app.main import create_app
from app.models.user import User,Role
from app.models.inspection import Inspection
from app.ocr.service import set_custom_ocr_provider
from app.ocr.providers.rapid import RapidOCRProvider

@pytest.fixture
def client(tmp_path):
 settings=Settings(_env_file=None,environment='test',database_url='sqlite://',jwt_secret=secrets.token_urlsafe(48),storage_local_dir=str(tmp_path/'evidence'),ocr_provider='rapid',ruleset_id='LMPC-2026-RULES')
 with TestClient(create_app(settings)) as client:
  Base.metadata.create_all(client.app.state.engine)
  with client.app.state.session_factory() as db:
   db.add_all([User(id='owner',full_name='Inspector',email='owner@example.com',hashed_password=hash_password('TestPassword123!'),role=Role.INSPECTOR),User(id='other',full_name='Other Inspector',email='other@example.com',hashed_password=hash_password('TestPassword123!'),role=Role.INSPECTOR)])
   db.commit()
  set_custom_ocr_provider(None)
  yield client
  set_custom_ocr_provider(None)

def headers(client,email='owner@example.com'):
 r=client.post('/api/v1/auth/login',json={'email':email,'password':'TestPassword123!'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['access_token']}

def label():
 image=np.full((700,1200,3),230,np.uint8)
 for i,line in enumerate(['Product Name: Roasted Almonds','Net Quantity: 500 g','MRP: Rs. 150.00','Manufactured by: APEX Foods','Best before 6 months from packaging']):
  cv2.putText(image,line,(35,85+i*110),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2)
 return cv2.imencode('.jpg',image)[1].tobytes()

def create(client,h):
 r=client.post('/api/v1/inspections',json={},headers=h);assert r.status_code==201,r.text
 return '/api/v1/inspections/'+r.json()['id']

def test_single_role_numbering_upload_resume_submit(client):
 h=headers(client)
 with client.app.state.session_factory() as db:
  db.add_all([Inspection(inspection_code='INS-2026-000001',created_by_user_id='owner'),Inspection(inspection_code='INS-2026-DEMO-Z',created_by_user_id='owner')]);db.commit()
 base=create(client,h)
 assert client.get(base,headers=h).json()['inspection_code']=='INS-2026-000002'
 r=client.post(base+'/images',files={'files':('label.jpg',label(),'image/jpeg')},data={'panel_types':'FRONT'},headers=h)
 assert r.status_code==201,r.text
 assert r.json()[0]['processing_result']['metrics']['blur_score']>=0
 resumed=client.get(base,headers=h).json()
 assert resumed['images_count']==1
 submitted=client.post(base+'/submit',headers=h)
 assert submitted.status_code==200,submitted.text
 assert submitted.json()['images'][0]['id']==r.json()[0]['id']
 assert client.get(base,headers=headers(client,'other@example.com')).status_code==404
 assert [role.value for role in Role]==['INSPECTOR']

def test_real_analysis_report_and_override(client):
 h=headers(client);base=create(client,h)
 assert client.post(base+'/images',files={'files':('label.jpg',label(),'image/jpeg')},data={'panel_types':'FRONT'},headers=h).status_code==201
 r=client.post(base+'/analysis',headers=h)
 assert r.status_code==200,r.text
 assert r.json()['candidate_count']>=3
 assert r.json()['evaluation']['total_rules']==12
 rows=client.get(base+'/evaluation/results',headers=h).json()
 assert all(row['verdict']=='UNCERTAIN' for row in rows)
 ocr=client.get(base+'/ocr/summary',headers=h).json()
 assert ocr['total_ocr_blocks']>=3
 image=client.get(base,headers=h).json()['images'][0]
 blocks=client.get(base+'/images/'+image['id']+'/ocr',headers=h).json()['blocks']
 assert blocks and all(b['relative_box'] and all(0<=v<=1 for v in b['relative_box']) for b in blocks)
 decision={'rule_id':rows[0]['rule_id'],'rule_key':rows[0]['rule_key'],'final_verdict':'PASS','override_reason':'Inspected the original label and confirmed this declaration.'}
 assert client.post(base+'/review/rule-decisions',json=decision,headers=h).status_code==200
 pdf=client.get(base+'/reports/pdf',headers=h)
 assert pdf.status_code==200,pdf.text[:200]
 assert pdf.content.startswith(b'%PDF-') and len(pdf.content)>10000

def test_invalid_file_never_counts_as_evidence(client):
 h=headers(client);base=create(client,h)
 assert client.post(base+'/images',files={'files':('fake.jpg',b'not an image','image/jpeg')},headers=h).status_code==422
 assert client.get(base,headers=h).json()['images_count']==0
 assert client.post(base+'/submit',headers=h).status_code==422
