"""Isolated standard Document ingestion. `status` never re-imports the fixture."""
import json
import sys
import time
import urllib.request
from pathlib import Path
from cloud_probe import call, token

ROOT='https://discoveryengine.googleapis.com/v1/projects/tdf-ocf/locations/global/collections/default_collection'
STORE='city-governance-chunk-validation-20260916'
BUCKET='tdf-ocf-city-governance-docs'
STATE=Path('/tmp/city-chunk-document-probe.json')


def main():
    endpoint=ROOT+'/dataStores/'+STORE
    phase=sys.argv[1]
    if phase=='prepare':
        if STATE.exists():raise SystemExit('Fixture exists; use status instead of re-importing.')
        config=call(endpoint)
        if config.get('documentProcessingConfig',{}).get('chunkingConfig'):
            raise SystemExit('Probe requires a standard document store without chunking.')
        schema=call(endpoint+'/schemas/default_schema')
        value=json.loads(schema['jsonSchema'])
        properties=value.setdefault('properties',{})
        for field in ['document_id','publication_key','chunk_id','language','city']:
            properties[field]={'type':'string','indexable':True,'retrievable':True}
        for field in ['content_sha256','original_sha256','original_uri']:
            properties[field]={'type':'string','retrievable':True}
        for field in ['version','page_start','page_end']:
            properties[field]={'type':'integer','retrievable':True}
        updated=call(endpoint+'/schemas/default_schema',{'jsonSchema':json.dumps(value)},'PATCH')
        if updated.get('error'):raise RuntimeError(updated['error'])
        corpus={
            'en':'City staff must assess privacy risks before using artificial intelligence. Automatic approval is prohibited.',
            'ja':'市職員は人工知能を使用する前にプライバシーリスクを評価しなければならない。自動承認は禁止されている。',
            'zh-tw':'市府使用人工智慧前必須評估隱私風險，禁止自動核准。',
            'unrelated':'The cafeteria serves rice and vegetables for lunch. The weather is sunny and warm.'}
        import hashlib
        def upload(key,data,mime):
            request=urllib.request.Request(f'https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o?uploadType=media&name={key}',
                data=data,headers={'Authorization':'Bearer '+token(),'Content-Type':mime},method='POST')
            with urllib.request.urlopen(request,timeout=30) as response:json.load(response)
            return f'gs://{BUCKET}/{key}'
        records=[]
        for language,content in corpus.items():
            identifier='cad-probe-'+language
            uri=upload('validation/chunk-doc-20260917/'+identifier+'.txt',content.encode(),'text/plain')
            records.append({'id':identifier,'structData':{'document_id':identifier,'publication_key':identifier+':1',
                'version':1,'chunk_id':'c1','title':identifier,'language':'zh-TW' if language=='zh-tw' else ('en' if language=='unrelated' else language),
                'city':'synthetic-test','page_start':1,'page_end':1,'content_sha256':hashlib.sha256(content.encode()).hexdigest()},
                'content':{'mimeType':'text/plain','uri':uri}})
        uri=upload('validation/chunk-doc-20260917/manifest.jsonl',('\n'.join(json.dumps(r) for r in records)+'\n').encode(),'application/x-ndjson')
        operation=call(endpoint+'/branches/0/documents:import',{'gcsSource':{'inputUris':[uri],'dataSchema':'document'},'reconciliationMode':'INCREMENTAL'})
        if 'name' not in operation:raise RuntimeError(str(operation))
        STATE.write_text(json.dumps({'operation':operation['name'],'ids':[r['id'] for r in records],'created_at':time.time()},indent=2))
        print(json.dumps(operation),flush=True)
    elif phase=='status':
        state=json.loads(STATE.read_text())
        result={'operation':call('https://discoveryengine.googleapis.com/v1/'+state['operation'])}
        result['documents']={identifier:call(endpoint+'/branches/0/documents/'+identifier).get('indexStatus') for identifier in state['ids']}
        result['search']={}
        for name,query,extra in [('en','privacy risk',''),('zh_to_en_ja','市府使用人工智慧之前必須評估哪一種風險？','language: ANY("en", "ja")'),
                                 ('en_to_zh','What risk must city employees assess before using AI?','language: ANY("zh-TW")')]:
            response=call(endpoint+'/servingConfigs/default_search:search',{'query':query,'pageSize':10,
                'filter':'city: ANY("synthetic-test")'+(' AND '+extra if extra else ''),'contentSearchSpec':{'searchResultMode':'DOCUMENTS'}})
            result['search'][name]={'error':response.get('error'),'semanticState':response.get('semanticState'),
                'ids':[r.get('document',{}).get('id') for r in response.get('results',[])]}
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        Path('/tmp/city-chunk-document-probe-status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    elif phase=='cleanup':
        from google.cloud import storage
        from google.oauth2.credentials import Credentials
        state=json.loads(STATE.read_text())
        assert set(state['ids'])=={'cad-probe-en','cad-probe-ja','cad-probe-zh-tw','cad-probe-unrelated'}
        for identifier in state['ids']:
            result=call(endpoint+'/branches/0/documents/'+identifier,method='DELETE')
            assert not result.get('error') or result.get('http_status')==404,result
        client=storage.Client(project='tdf-ocf',credentials=Credentials(token()))
        for blob in client.list_blobs(BUCKET,prefix='validation/chunk-doc-20260917/'):
            blob.delete()
        STATE.rename('/tmp/city-chunk-document-probe-completed.json')
        print('Only the four synthetic probe Documents and their GCS fixtures were deleted.')
    else:raise SystemExit('Use prepare, status or cleanup')


if __name__=='__main__':main()
