"""Synthetic cross-language acceptance corpus; never modifies the research datastore."""
import json
import time
import urllib.request
from pathlib import Path
from cloud_probe import call, token

ROOT='https://discoveryengine.googleapis.com/v1alpha/projects/tdf-ocf/locations/global/collections/default_collection'
STORE='city-governance-chunk-validation-20260916-v2'
BUCKET='tdf-ocf-city-governance-docs'
PREFIX='validation/20260916-chunks'

def upload(name,value,mime):
    key=PREFIX+'/'+name
    request=urllib.request.Request(f'https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o?uploadType=media&name={key}',
        data=value,headers={'Authorization':'Bearer '+token(),'Content-Type':mime},method='POST')
    with urllib.request.urlopen(request,timeout=120) as response:
        json.load(response)
    return f'gs://{BUCKET}/{key}'

if __name__=='__main__':
    corpus={
        'en':'Synthetic test policy: City employees must assess privacy risks before using artificial intelligence. Automatic approval is prohibited. In 2026, 20 cases required human review.',
        'zh-TW':'合成測試政策：市府人員在使用人工智慧前，必須評估隱私風險。禁止自動核准。2026 年有 20 件案件需要人工審查。',
        'ja':'合成テスト方針：市職員は人工知能を使用する前にプライバシーリスクを評価しなければならない。自動承認は禁止されている。2026 年には 20 件の案件で人による審査が必要だった。'}
    manifests=[]
    for language,text in corpus.items():
        identifier='synthetic-language-'+language.lower()
        original=upload(identifier+'.txt',text.encode(),'text/plain')
        chunk=upload(identifier+'.json',json.dumps({'documentMetadata':{'title':identifier,'uri':original},
            'chunks':[{'id':'policy','content':text,'pageSpan':{'pageStart':1,'pageEnd':1}}]},ensure_ascii=False).encode(),'application/json')
        manifests.append({'id':identifier,'structData':{'title':identifier,'language':language},
            'content':{'mimeType':'application/json','uri':chunk}})
    uri=upload('multilingual-manifest.jsonl',('\n'.join(json.dumps(m) for m in manifests)+'\n').encode(),'application/x-ndjson')
    result=call(f'{ROOT}/dataStores/{STORE}/branches/0/documents:import',{'gcsSource':{'inputUris':[uri],'dataSchema':'document'}})
    print(json.dumps({'import':result}),flush=True)
    if not result.get('name'):
        raise SystemExit(1)
    for _ in range(120):
        operation=call('https://discoveryengine.googleapis.com/v1alpha/'+result['name'])
        if operation.get('done'):
            print(json.dumps({'operation':operation}),flush=True)
            break
        time.sleep(5)
    if not operation.get('done') or operation.get('error') or operation.get('response',{}).get('errorSamples') or int(operation.get('metadata',{}).get('failureCount',0)):
        Path('/tmp/city-multilingual-probe.json').write_text(json.dumps({'import':operation,'accepted':False},indent=2))
        raise SystemExit('Import did not complete successfully; search acceptance remains pending.')
    endpoint=ROOT+'/engines/city-chunk-validation-20260916/servingConfigs/default_search:search'
    cases=[('zh_to_en_ja','使用人工智慧前，城市員工必須先評估哪一種風險？',None),
           ('en_to_zh','What risks must city employees assess before using artificial intelligence?','language: ANY("zh-TW")'),
           ('en_only','What risks must city employees assess before using artificial intelligence?','language: ANY("en")')]
    output={'import':operation,'search':{}}
    for name,query,filter_expr in cases:
        response=call(endpoint,{'query':query,'pageSize':10,'filter':filter_expr or '', 'contentSearchSpec':{'searchResultMode':'CHUNKS'}})
        output['search'][name]={'error':response.get('error'),'semantic_state':response.get('semanticState'),
            'chunks':[{'name':r.get('chunk',{}).get('name'),'content':r.get('chunk',{}).get('content')} for r in response.get('results',[])]}
    Path('/tmp/city-multilingual-probe.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(json.dumps(output,ensure_ascii=False,indent=2))

    if not all(case['chunks'] and not case.get('error') for case in output['search'].values()):
        raise SystemExit('Cross-language search acceptance failed.')
