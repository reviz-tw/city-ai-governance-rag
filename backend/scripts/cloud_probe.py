"""Read-only model / datastore smoke check; never print credentials or documents."""
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

def token():
    return subprocess.run(['gcloud','auth','print-access-token','--account','hcchien@reviz.tw'], check=True, capture_output=True, text=True).stdout.strip()

def call(url, data=None, method=None):
    request=urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization':'Bearer '+token(),'Content-Type':'application/json','x-goog-user-project':'tdf-ocf'}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=150) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {'http_status':exc.code, 'error':json.loads(exc.read()).get('error',{}).get('message','')}

if __name__ == '__main__':
    output={}
    for model in ['gemini-3.7-flash','gemini-3.5-flash-lite']:
        result=call(f'https://aiplatform.googleapis.com/v1/projects/tdf-ocf/locations/global/publishers/google/models/{model}:generateContent',
                    {'contents':[{'role':'user','parts':[{'text':'Reply with the single word OK.'}]}], 'generationConfig':{'maxOutputTokens':128}})
        output[model]={'ok':bool(result.get('candidates')), 'error':result.get('error'), 'usage':result.get('usageMetadata')}
    output['data_store']=call('https://discoveryengine.googleapis.com/v1alpha/projects/tdf-ocf/locations/global/collections/default_collection/dataStores/city-governance-datastore')
    print(json.dumps(output, ensure_ascii=False, indent=2))
