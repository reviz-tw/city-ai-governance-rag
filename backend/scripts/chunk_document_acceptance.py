"""Dev-only publication acceptance via the same authenticated HTTP APIs as Admin UI.

Synthetic session identity is used only for API testing, not Google-login acceptance.
Secrets stay in memory. prepare/edit/rollback each submit once; status never reimports.
"""
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
import jwt
import requests

PROJECT='tdf-ocf'
ORIGIN=os.environ.get('ACCEPTANCE_ORIGIN','https://candidate---city-rag-backend-dev-wvswpuk2tq-de.a.run.app')
STATE=Path('/tmp/city-chunk-document-acceptance.json')
access=subprocess.check_output(['gcloud','auth','print-access-token','--account=hcchien@reviz.tw'],text=True).strip()
r=requests.get(f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets/city-governance-session/versions/latest:access',headers={'Authorization':'Bearer '+access},timeout=30)
r.raise_for_status();signing=base64.b64decode(r.json()['payload']['data']).decode()
state=json.loads(STATE.read_text()) if STATE.exists() else {}


def save():STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))


def api(path,data=None,method='GET',reader=False,files=None,raw=False,bearer=None):
    now=int(time.time())
    cookie=jwt.encode(dict(sub=state['owner']+('-reader' if reader else ''),email='hcchien@gmail.com' if reader else 'hcchien@reviz.tw',
        iss='city-governance',aud='city-governance',iat=now,exp=now+300),signing,algorithm='HS256')
    headers={'Origin':ORIGIN,'Accept':'application/json, text/event-stream'}
    if bearer:headers['Authorization']='Bearer '+bearer
    else:headers['Cookie']='governance_session='+cookie
    response=requests.request(method,ORIGIN+path,headers=headers,files=files,data=data if files else None,
        json=None if files else data,timeout=180)
    if response.status_code>=400:return {'http_status':response.status_code}
    if raw:return response.content
    if 'text/event-stream' in response.headers.get('Content-Type',''):
        return [json.loads(line[6:]) for line in response.content.decode('utf-8').split('\n') if line.startswith('data: ')]
    return response.json()


def doc(language):return api('/api/library/'+state['documents'][language]['id'])


def publish(language,rollback=False):
    d=doc(language);path='/api/library/'+d['id']
    payload={'revision':d['draft_revision']}
    if not rollback:payload['reviewed_diff']=api(path+'/diff')['hash']
    job=api(path+('/rollback' if rollback else '/publish'),payload,'POST')
    assert 'id' in job,job
    state['jobs'].append(job['id']);save()
    print(json.dumps({'language':language,'job':job['id'],'status':job['status']}),flush=True)


phase=sys.argv[1]
if phase=='prepare':
    if state:raise SystemExit('Fixture already exists; use status.')
    state={'owner':'cad-acceptance-'+uuid.uuid4().hex,'documents':{},'jobs':[],'phase':'v1','created_at':time.time()};save()
    from reportlab.pdfgen import canvas
    buffer=io.BytesIO();pdf=canvas.Canvas(buffer)
    english=['City staff must assess privacy risks before using artificial intelligence.',
             'Automatic approval is prohibited. Human review is mandatory for all AI decisions.']
    for text in english:
        pdf.drawString(40,780,text);pdf.showPage()
    pdf.save()
    corpus={'en':('acceptance-policy.pdf',buffer.getvalue(),'application/pdf'),
        'ja':('acceptance-policy-ja.txt','市職員は人工知能を使用する前にプライバシーリスクを評価しなければならない。自動承認は禁止されている。人間による審査が必要です。'.encode(),'text/plain'),
        'zh-TW':('acceptance-policy-zh.txt','市府使用人工智慧前必須評估隱私風險。禁止自動核准，必須由人員審查。'.encode(),'text/plain')}
    for language,upload in corpus.items():
        d=api('/api/library',{'language':language,'city':state['owner'],'rights_confirmed':'true'},'POST',files={'file':upload})
        assert d.get('id'),d
        state['documents'][language]={'id':d['id'],'original_hash':hashlib.sha256(upload[1]).hexdigest()};save()
        d=doc(language);assert d['indexing_enabled'] and d['published_version']==0
        assert api('/api/library/'+d['id'],reader=True).get('http_status')==404
        if language=='en':
            values=[dict(id='c'+str(i+1),order=i,content=b['text'],refs=[dict(block_id=b['id'],page=b['page'],start=0,end=len(b['text']))]) for i,b in enumerate(d['blocks'])]
            d=api('/api/library/'+d['id']+'/draft',{'revision':d['draft_revision'],'chunks':values},'POST')
            assert len(d['draft'])==2
        state['documents'][language]['v1_chunks']=d['draft'];save()
        publish(language)
    print('Private multilingual fixtures uploaded and submitted once; original PDF has two pages.',flush=True)
elif phase=='status':
    for language,item in state['documents'].items():
        d=doc(language)
        publications=api('/api/library/'+d['id']+'/publications')
        print(json.dumps({'language':language,'published_version':d['published_version'],'index_status':d['index_status'],
            'publications':[{k:p.get(k) for k in ['version','status','operation','error']} for p in publications]},ensure_ascii=False),flush=True)
    for identifier in state['jobs']:
        job=api('/api/artifacts/'+identifier)
        print(json.dumps({'job':identifier,'status':job.get('status'),'progress':job.get('progress'),'error':job.get('error'),'result':job.get('result')}),flush=True)
elif phase=='edit':
    assert state['phase']=='v1'
    for language,item in state['documents'].items():
        d=doc(language);assert d['published_version']==1,d['index_status']
        checked=api('/api/library/'+d['id']+'/indexed-chunks');assert checked['verified'] and checked['chunks']==item['v1_chunks']
    d=doc('en');parts=d['draft'];merged='\n\n'.join(p['content'] for p in parts)+' An independent audit is required annually.'
    refs=[ref for part in parts for ref in part['refs']]
    changed=[dict(id='merged-policy',order=0,content=merged,refs=refs)]
    d=api('/api/library/'+d['id']+'/draft',{'revision':d['draft_revision'],'chunks':changed},'POST')
    assert d['published_version']==1
    state['documents']['en']['v2_chunks']=changed;state['phase']='v2';save();publish('en')
    assert doc('en')['published_version']==1
    print('Draft saved and v2 submitted; v1 remains active until Search verification.',flush=True)
elif phase=='rollback':
    assert state['phase']=='v2'
    d=doc('en');assert d['published_version']==2
    checked=api('/api/library/'+d['id']+'/indexed-chunks')
    assert checked['verified'] and checked['chunks']==state['documents']['en']['v2_chunks']
    state['phase']='rollback';save();publish('en',True)
    assert doc('en')['published_version']==2
elif phase=='verify':
    for language,item in state['documents'].items():
        d=doc(language);expected=3 if language=='en' else 1
        assert d['published_version']==expected,(language,d['index_status'])
        checked=api('/api/library/'+d['id']+'/indexed-chunks')
        assert checked['verified'] and checked['chunks']==item['v1_chunks']
        original=api('/api/library/'+d['id']+'/original',raw=True)
        assert hashlib.sha256(original).hexdigest()==item['original_hash']
        if 'hcchien@gmail.com' not in d.get('readers',[]):
            assert api('/api/library/'+d['id'],reader=True).get('http_status')==404
        d=api('/api/library/'+d['id']+'/sharing',{'revision':d['draft_revision'],'shared':False,'readers':['hcchien@gmail.com']},'PATCH')
        assert api('/api/library/'+d['id'],reader=True).get('id')==d['id']
        denied=api('/api/library/'+d['id']+'/publish',{'revision':d['draft_revision'],'reviewed_diff':'none'},'POST',reader=True)
        assert denied.get('http_status')==403,denied
    question='市府使用人工智慧前應該評估哪種風險？誰必須審查決策？'
    events=api('/api/chat/stream',{'query':question,'city':state['owner'],'response_language':'zh-TW','source_languages':['en','ja']},'POST',reader=True)
    assert events[-1].get('status')=='completed',events[-1]
    source_events=[e for e in events if e.get('type')=='sources'];assert source_events,events
    evidence=source_events[0]['sources']
    assert {s['document_id'] for s in evidence}>={state['documents']['en']['id'],state['documents']['ja']['id']},evidence
    assert all(s.get('chunk_id') and s.get('version') in [1,3] for s in evidence),evidence
    print(json.dumps({'frontend_stream_sources':evidence},ensure_ascii=False),flush=True)
    credential=api('/api/auth/mcp-token',{},'POST',reader=True)['token']
    result=api('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'ask_city_ai_governance_rag','arguments':{
        'question':question,'city':state['owner'],'response_language':'zh-TW','source_languages':['en','ja']}}},'POST',bearer=credential)
    if isinstance(result,list):result=result[-1]
    assert not result.get('result',{}).get('isError'),result
    answer=json.loads(result['result']['content'][0]['text'])
    assert answer.get('status')=='completed',answer.get('status')
    assert {s['document_id'] for s in answer['sources']}>={state['documents']['en']['id'],state['documents']['ja']['id']},answer
    api('/api/auth/mcp-token',method='DELETE',reader=True)
    print(json.dumps({'original_hashes':'unchanged','rollback':'v3 equals v1','reader_publish':403,
        'frontend_cross_language':'passed','mcp_cross_language':'passed','mcp_sources':answer['sources']},ensure_ascii=False),flush=True)
elif phase=='mcp-read':
    credential=api('/api/auth/mcp-token',{},'POST',reader=True)['token']
    try:
        for languages in [['en','ja'],['en']]:
            result=api('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'search_city_ai_governance_knowledge','arguments':{
                'query':'市府使用人工智慧前應該評估哪種風險？','city':state['owner'],'source_languages':languages}}},'POST',bearer=credential)
            if isinstance(result,list):result=result[-1]
            found=json.loads(result['result']['content'][0]['text'])
            assert found and all(r['metadata']['language'] in languages for r in found),found
            if len(languages)>1:assert {r['metadata']['language'] for r in found}==set(languages)
            for item in found:
                language=item['metadata']['language']
                original=next(c for c in state['documents'][language]['v1_chunks'] if c['id']==item['chunk_id'])
                assert item['snippets'][0]['snippet']==original['content']
            print(json.dumps({'mcp_source_languages':languages,'full_unicode_content':'exact canonical match','results':len(found)},ensure_ascii=False),flush=True)
    finally:api('/api/auth/mcp-token',method='DELETE',reader=True)
elif phase=='remote':
    from chunk_document_probe import call,ROOT,STORE
    from app.services.chunks import index_prefix
    for language,item in state['documents'].items():
        versions=api('/api/library/'+item['id']+'/publications')
        active=doc(language)['published_version']
        for pub in versions:
            for chunk in pub['chunks']:
                identifier=index_prefix(item['id'],pub['version'])+'-'+hashlib.sha256(chunk['id'].encode()).hexdigest()[:24]
                result=call(ROOT+'/dataStores/'+STORE+'/branches/0/documents/'+identifier)
                assert (result.get('http_status')==404) if pub['version']!=active else (result.get('id')==identifier),result
        print(json.dumps({'language':language,'active_version':active,'old_remote_documents':'404','current_remote_documents':'present'}),flush=True)
elif phase=='cleanup':
    from cloud_database import connect
    from google.cloud import storage
    from sqlalchemy import select,delete
    from app.services import store
    from app.services.chunks import index_prefix
    from chunk_document_probe import call,ROOT,STORE
    credential=connect();client=storage.Client(project=PROJECT,credentials=credential)
    assert state['owner'].startswith('cad-acceptance-')
    with store.session() as db:
        for item in state['documents'].values():
            d=db.get(store.Document,item['id']);assert d.owner==state['owner'] and d.metadata_json['city']==state['owner']
            assert d.original_key.startswith('managed-originals/'+d.id+'/')
            publications=list(db.scalars(select(store.Publication).where(store.Publication.document_id==d.id)))
            for pub in publications:
                for chunk in pub.chunks:
                    identifier=index_prefix(d.id,pub.version)+'-'+hashlib.sha256(chunk['id'].encode()).hexdigest()[:24]
                    deleted=call(ROOT+'/dataStores/'+STORE+'/branches/0/documents/'+identifier,method='DELETE')
                    assert not deleted.get('error') or deleted.get('http_status')==404,deleted
            for bucket_name,prefix in [('tdf-ocf-city-governance-artifacts','managed-originals/'+d.id+'/'),
                ('tdf-ocf-city-governance-docs','managed-originals/'+d.id+'/'),('tdf-ocf-city-governance-docs','managed-chunks/'+d.id+'/')]:
                for blob in client.list_blobs(bucket_name,prefix=prefix):blob.delete()
            for model in [store.Publication,store.DraftRevision]:db.execute(delete(model).where(model.document_id==d.id))
            db.delete(d)
        for identifier in state['jobs']:
            job=db.get(store.Job,identifier);assert job.owner==state['owner'] and job.status=='completed';db.delete(job)
        db.execute(delete(store.MCPToken).where(store.MCPToken.owner.in_([state['owner'],state['owner']+'-reader'])))
        db.execute(delete(store.RateLimit).where(store.RateLimit.key.like(state['owner']+'%')))
        db.commit()
    STATE.rename('/tmp/city-chunk-document-acceptance-completed.json')
    print('Only acceptance fixture documents, publications, jobs and frozen GCS objects deleted.',flush=True)
else:raise SystemExit('Use prepare, status, edit, rollback, verify, mcp-read, remote, cleanup')
