import json
from cloud_probe import call
BASE='https://discoveryengine.googleapis.com/v1alpha/projects/tdf-ocf/locations/global/collections/default_collection/dataStores/'
store='city-governance-chunk-validation-20260916-v2'
output={}
for language,query in [('en','AI transparency privacy public oversight'),('zh-TW','人工智慧透明度與隱私需要公眾監督'),('ja','人工知能の透明性とプライバシーには公的な監視が必要です')]:
    result=call(BASE+store+'/servingConfigs/default_search:search', {'query':query,'pageSize':5,'contentSearchSpec':{'searchResultMode':'CHUNKS'}})
    output[language]={'error':result.get('error'),'chunks':[item.get('chunk',{}).get('id') for item in result.get('results',[])]}
filtered=call(BASE+store+'/servingConfigs/default_search:search', {'query':'AI transparency','pageSize':5,'filter':'language: ANY("en")','contentSearchSpec':{'searchResultMode':'CHUNKS'}})
output['filter_en']={'error':filtered.get('error'),'chunks':[item.get('chunk',{}).get('id') for item in filtered.get('results',[])]}
print(json.dumps(output,ensure_ascii=False,indent=2))
