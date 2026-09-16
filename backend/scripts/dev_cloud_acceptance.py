"""Controlled dev integration fixture, separate from real Google-login verification.

Requires Cloud SQL Auth Proxy on localhost:54329. Credentials are read in memory
from Secret Manager, never persisted or printed. All writes are restricted to
randomly named fixture records/objects; existing research documents are untouched.
"""
import base64
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path
import jwt
from google.cloud import storage
from google.oauth2.credentials import Credentials
from sqlalchemy import create_engine, select, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.services import store

PROJECT='tdf-ocf'
ORIGIN='https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app'
STATE=Path('/tmp/city-dev-acceptance.json')
access=subprocess.run(['gcloud','auth','print-access-token','--account=hcchien@reviz.tw'],check=True,capture_output=True,text=True).stdout.strip()

def secret(name):
    request=urllib.request.Request(f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets/{name}/versions/latest:access',headers={'Authorization':'Bearer '+access})
    with urllib.request.urlopen(request,timeout=30) as response:
        return base64.b64decode(json.load(response)['payload']['data']).decode()

signing=secret('city-governance-session')
url=make_url(secret('city-governance-database-url')).set(host='127.0.0.1',port=54329,query={})
engine=create_engine(url,hide_parameters=True,pool_size=1,max_overflow=0)
bucket=storage.Client(project=PROJECT,credentials=Credentials(access)).bucket('tdf-ocf-city-governance-artifacts')
state=json.loads(STATE.read_text()) if STATE.exists() else {}

def api(path,data=None,method=None,other=False,bearer=None,raw=False):
    subject=state['owner']+('-other' if other else '')
    now=int(time.time())
    cookie=jwt.encode(dict(sub=subject,email='hcchien@gmail.com',iss='city-governance',aud='city-governance',iat=now,exp=now+300),signing,algorithm='HS256')
    headers={'Origin':ORIGIN,'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    if bearer: headers['Authorization']='Bearer '+bearer
    else: headers['Cookie']='governance_session='+cookie
    request=urllib.request.Request(ORIGIN+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
    try:
        with urllib.request.urlopen(request,timeout=180) as response:
            body=response.read()
            if raw:return body
            if 'text/event-stream' in response.headers.get('Content-Type',''):
                return [json.loads(line[6:]) for line in body.decode().splitlines() if line.startswith('data: ')][-1]
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        return {'http_status':exc.code}

phase=sys.argv[1]
if phase=='prepare':
    if state:raise SystemExit('Existing fixture state found; use status/confirm/cleanup.')
    identifier='acceptance-'+uuid.uuid4().hex
    state={'owner':'dev-fixture-'+uuid.uuid4().hex,'document':identifier,'jobs':{},'created_at':time.time()}
    original='# Synthetic policy\n\nIn 2026, 20 cases required human review. Automatic approval is prohibited.\n\nCity staff must assess privacy risks before using artificial intelligence.'
    blocks=[dict(id=f'p{i+1}',text=text,page=None,kind='heading' if i==0 else 'paragraph',cells=None) for i,text in enumerate(original.split('\n\n'))]
    key=f'originals/{identifier}/synthetic.txt'
    bucket.blob(key).upload_from_string(original,content_type='text/plain')
    with Session(engine) as db:
        db.add(store.Document(id=identifier,owner=state['owner'],title='Synthetic dev acceptance policy',language='en',original_key=key,
            original_hash=hashlib.sha256(original.encode()).hexdigest(),mime='text/plain',blocks=blocks,draft=[],metadata_json={'synthetic_acceptance':True}))
        db.commit()
    STATE.write_text(json.dumps(state))
    assert api('/api/library/'+identifier,other=True).get('http_status')==404
    for kind,language in [('pdf','zh-TW'),('pptx','zh-TW'),('chart','zh-TW'),('translation','ja')]:
        payload={'kind':kind,'language':language,'scope':'document' if kind=='translation' else 'answer','source_ids':[identifier],
            'message_ids':[] if kind=='translation' else ['synthetic-answer'],'context':'Synthetic verification only. State the privacy prerequisite, no automatic approval, and 20 reviewed cases in 2026.'}
        job=api('/api/artifacts',payload)
        if 'id' not in job:raise RuntimeError('Fixture task creation failed: '+str(job))
        state['jobs'][kind]=job['id'];STATE.write_text(json.dumps(state))
    print(json.dumps({'fixture_created':identifier,'tasks':state['jobs'],'cross_user_document':'404'}),flush=True)
elif phase=='status':
    for kind,identifier in state['jobs'].items():
        job=api('/api/artifacts/'+identifier)
        result={'kind':kind,'status':job.get('status'),'error':job.get('error'),'progress':job.get('progress')}
        if job.get('status')=='awaiting_review':result['draft']=job['draft']
        if job.get('result'):result['files']=[f['name'] for f in job['result'].get('files',[])]
        if kind=='translation' and job.get('draft'):result['translation']=[b['text'] for b in job['draft'].get('blocks',[])]
        print(json.dumps(result,ensure_ascii=False),flush=True)
elif phase=='export-drafts':
    drafts={}
    for kind,identifier in state['jobs'].items():
        job=api('/api/artifacts/'+identifier)
        if job.get('status')=='awaiting_review':
            drafts[identifier]={'revision':job['revision'],'draft':job['draft']}
    Path('/tmp/city-reviewed-drafts.json').write_text(json.dumps(drafts,ensure_ascii=False,indent=2))
    print('Drafts exported for review to /tmp/city-reviewed-drafts.json')
elif phase=='confirm':
    reviewed=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else None
    for kind,identifier in state['jobs'].items():
        job=api('/api/artifacts/'+identifier)
        if job.get('status')=='awaiting_review':
            value=reviewed[identifier] if reviewed is not None else {'revision':job['revision'],'draft':job['draft']}
            assert value['revision']==job['revision']
            changed=api(f'/api/artifacts/{identifier}/confirm',value)
            print(kind,changed.get('status'),flush=True)
elif phase=='rerender':
    # Only this script's isolated fixtures; reuse already-reviewed drafts to
    # exercise a renderer update without additional model requests.
    if not state['owner'].startswith('dev-fixture-'):
        raise RuntimeError('Not an acceptance fixture')
    with Session(engine) as db:
        for kind,identifier in state['jobs'].items():
            if kind=='translation':continue
            job=db.get(store.Job,identifier)
            assert job.owner==state['owner'] and job.status=='completed'
            job.status='awaiting_review';job.revision+=1;job.result=None
        db.commit()
    print('Fixture drafts ready for renderer recheck; run confirm.')
elif phase=='download':
    out=Path('/tmp/city-cloud-artifacts');out.mkdir(exist_ok=True)
    for kind,identifier in state['jobs'].items():
        job=api('/api/artifacts/'+identifier)
        assert job.get('status')=='completed',(kind,job.get('status'),job.get('error'))
        assert api('/api/artifacts/'+identifier,other=True).get('http_status')==404
        for file in job['result']['files']:
            data=api(f'/api/artifacts/{identifier}/download/'+file['name'],raw=True)
            assert isinstance(data,bytes) and len(data)>50
            (out/file['name']).write_bytes(data)
            print(json.dumps({'kind':kind,'file':file['name'],'bytes':len(data),'other_user':'404'}),flush=True)
elif phase=='expiry':
    identifier='expiry-'+uuid.uuid4().hex
    key=f'jobs/{identifier}/expiry.txt'
    bucket.blob(key).upload_from_string('Synthetic expired artifact',content_type='text/plain')
    with Session(engine) as db:
        db.add(store.Job(id=identifier,owner=state['owner'],email='hcchien@gmail.com',kind='pdf',status='completed',
                         payload={},expires_at=time.time()-60,result={'files':[{'name':'expiry.txt','key':key,'mime':'text/plain'}]}))
        db.commit()
    assert api('/api/artifacts/'+identifier).get('http_status')==404
    subprocess.run(['gcloud','scheduler','jobs','run','city-governance-cleanup','--location=asia-east1',
                    '--project=tdf-ocf','--account=hcchien@reviz.tw'],check=True,capture_output=True)
    for _ in range(10):
        with Session(engine) as db: exists=db.get(store.Job,identifier) is not None
        if not exists and not bucket.blob(key).exists():break
        time.sleep(5)
    else:raise RuntimeError('Scheduled expiry cleanup did not finish within the acceptance window')
    print(json.dumps({'expired_download':404,'scheduled_database_delete':True,'scheduled_object_delete':True}),flush=True)
elif phase=='benchmark-source':
    # Read the same existing policy used for the browser report; never publish it.
    document=api('/api/library/legacy-826492ab2d067b367b04e1d6d76e412e')
    assert document.get('blocks') and document.get('original_hash')
    Path('/tmp/city-model-benchmark-source.json').write_text(json.dumps({
        'title':document['title'],'id':document['id'],'version':document['original_hash'],
        'blocks':document['blocks']},ensure_ascii=False))
    print(json.dumps({'source':document['title'],'blocks':len(document['blocks'])}),flush=True)
elif phase=='continuation':
    # Resume this fixture's already translated blocks; no additional generation.
    import google.auth
    from app.core.config import settings
    from app.services import jobs
    settings.DATABASE_URL=url.render_as_string(hide_password=False)
    settings.CLOUD_TASKS_QUEUE='city-governance-jobs'
    settings.GCP_PROJECT_ID=PROJECT
    settings.GCP_REGION='asia-east1'
    settings.APP_ORIGIN=ORIGIN
    settings.WORKER_SERVICE_ACCOUNT='city-governance-worker@tdf-ocf.iam.gserviceaccount.com'
    store.engine.cache_clear()
    with Session(engine) as db:
        job=db.get(store.Job,state['jobs']['translation'])
        assert job.owner==state['owner'] and job.status=='completed'
        job.status='running';job.attempt+=1
        job.lease_until=time.time()+300
        db.commit();db.refresh(job);db.expunge(job)
    previous=google.auth.default
    google.auth.default=lambda **kwargs:(Credentials(token=access),PROJECT)
    try:
        jobs.defer(job,delay=20,progress=90)
    finally:
        google.auth.default=previous
    queued=api('/api/artifacts/'+job.id)
    assert queued['status']=='queued'
    print(json.dumps({'scheduled_continuation':'queued','id':job.id}),flush=True)
elif phase=='language-contract':
    for options in [{'response_language':'ar'},{'source_languages':['ar']}]:
        assert api('/api/chat/stream',{'query':'Synthetic language contract check',**options}).get('http_status')==422
    assert api('/api/artifacts',{'kind':'translation','scope':'document','source_ids':[state['document']],
                                 'language':'ar'}).get('http_status')==422
    print(json.dumps({'removed_answer_language':422,'removed_source_language':422,'removed_translation_language':422}),flush=True)
elif phase=='mcp':
    credential=api('/api/auth/mcp-token',{},method='POST')['token']
    initialized=api('/mcp',{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'dev-acceptance','version':'1'}}},bearer=credential)
    listed=api('/mcp',{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},bearer=credential)
    names=[t['name'] for t in listed.get('result',{}).get('tools',[])]
    assert 'ask_city_ai_governance_rag' in names and 'create_governance_report' in names,listed
    read=api('/mcp',{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'read_governance_document','arguments':{'document_id':state['document']}}},bearer=credential)
    assert not read.get('result',{}).get('isError'),read
    answer=api('/mcp',{'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'ask_city_ai_governance_rag','arguments':{'question':'政府使用生成式 AI 有哪些治理原則？','response_language':'ja','source_languages':['zh-TW']}}},bearer=credential)
    assert not answer.get('result',{}).get('isError'),answer
    content=answer['result']['content'][0]['text']
    parsed=json.loads(content)
    assert parsed.get('sources') and any('\u3040'<=char<='\u30ff' for char in parsed.get('answer',''))
    print(json.dumps({'mcp_rag_language':'ja','sources':len(parsed['sources']),'model':parsed.get('model_used')}),flush=True)
    api('/api/auth/mcp-token',method='DELETE')
    revoked=api('/mcp',{'jsonrpc':'2.0','id':4,'method':'tools/list','params':{}},bearer=credential)
    assert revoked.get('http_status')==401
    print(json.dumps({'mcp_initialized':'result' in initialized,'tools':names,'source_read':'passed','revoked_status':401}),flush=True)
elif phase=='cleanup':
    for identifier in state['jobs'].values():
        response=api('/api/artifacts/'+identifier,method='DELETE')
        assert response.get('success'),response
    with Session(engine) as db:
        doc=db.scalar(select(store.Document).where(store.Document.id==state['document'],store.Document.owner==state['owner']))
        if not doc or not doc.metadata_json.get('synthetic_acceptance'):raise RuntimeError('Fixture identity mismatch')
        bucket.blob(doc.original_key).delete()
        db.delete(doc)
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner==state['owner']))
        db.execute(delete(store.RateLimit).where(store.RateLimit.key.like(state['owner']+':%')))
        db.commit()
    STATE.rename('/tmp/city-dev-acceptance-completed.json')
    print('Synthetic fixture records and objects deleted; downloaded validation artifacts retained locally.')
else:raise SystemExit('Use prepare, status, confirm, download, mcp or cleanup')
