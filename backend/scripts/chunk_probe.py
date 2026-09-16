"""Isolated synthetic BYO-chunk compatibility test; preserves existing data stores."""
import json
import time
from cloud_probe import call
BASE='https://discoveryengine.googleapis.com/v1alpha/projects/tdf-ocf/locations/global/collections/default_collection'
STORE='city-governance-chunk-validation-20260916-v2'
if __name__ == '__main__':
    result=call(f'{BASE}/dataStores/{STORE}')
    if result.get('http_status') == 404:
        result=call(f'{BASE}/dataStores?dataStoreId={STORE}', {'displayName':'City governance synthetic chunk validation', 'industryVertical':'GENERIC', 'contentConfig':'CONTENT_REQUIRED', 'solutionTypes':['SOLUTION_TYPE_SEARCH'], 'documentProcessingConfig':{'chunkingConfig':{'layoutBasedChunkingConfig':{'chunkSize':500,'includeAncestorHeadings':True}},'defaultParsingConfig':{'layoutParsingConfig':{}}}})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    bucket='tdf-ocf-city-governance-docs'
    prefix='validation/20260916-chunks'
    root=f'{BASE}/dataStores/{STORE}/branches/0'
    original=b'Synthetic governance test. Version one has two passages.'
    import urllib.request
    from cloud_probe import token
    def upload(name, data, mime):
        request=urllib.request.Request(f'https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={prefix}/{name}', data=data,
            headers={'Authorization':'Bearer '+token(),'Content-Type':mime}, method='POST')
        with urllib.request.urlopen(request, timeout=120) as response:
            json.load(response)
        return f'gs://{bucket}/{prefix}/{name}'
    original_uri=upload('source.txt', original, 'text/plain')
    for version, chunks in [(1,[{'id':'a','content':'Synthetic A: AI transparency requires public oversight.','pageSpan':{'pageStart':1,'pageEnd':1}}, {'id':'b','content':'Synthetic B: privacy risk needs assessment.','pageSpan':{'pageStart':1,'pageEnd':1}}]), (2,[{'id':'merged','content':'Synthetic merged v2: AI transparency and privacy risk require public oversight and assessment.','pageSpan':{'pageStart':1,'pageEnd':1}}])]:
        payload={'documentMetadata':{'title':'Synthetic governance chunk validation','uri':original_uri},'chunks':chunks}
        uri=upload(f'chunks-v{version}.json', json.dumps(payload).encode(), 'application/json')
        manifest={'id':'synthetic-chunk-document','structData':{'title':'Synthetic governance chunk validation','language':'en'},'content':{'mimeType':'application/json','uri':uri}}
        manifest_uri=upload(f'manifest-v{version}.jsonl', (json.dumps(manifest)+'\n').encode(), 'application/x-ndjson')
        result=call(f'{root}/documents:import', {'gcsSource':{'inputUris':[manifest_uri],'dataSchema':'document'},'reconciliationMode':'INCREMENTAL'})
        print(json.dumps({'version':version,'import':result}), flush=True)
        if not result.get('name'):
            break
        for attempt in range(90):
            operation=call('https://discoveryengine.googleapis.com/v1alpha/'+result['name'])
            if operation.get('done'):
                print(json.dumps({'version':version,'operation':operation}), flush=True)
                break
            time.sleep(10)
        actual=call(f'{root}/documents/synthetic-chunk-document/chunks')
        print(json.dumps({'version':version,'chunks':actual}), flush=True)
        Path = __import__('pathlib').Path
        Path(f'/tmp/city-chunk-probe-v{version}.json').write_text(json.dumps({'operation':operation,'chunks':actual}))
