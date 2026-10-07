"""Use the user's existing Cloud IAM credentials; never create web sessions."""
import base64
from datetime import datetime, timedelta
import json
import subprocess
import requests
import google.auth
from google.auth.credentials import Credentials
from sqlalchemy.engine import make_url

ACCOUNT='hcchien@reviz.tw'
PROJECT='tdf-ocf'

class GcloudCredentials(Credentials):
    def refresh(self, request):
        self.token=subprocess.check_output(['gcloud','auth','print-access-token','--account='+ACCOUNT],text=True).strip()
        self.expiry=datetime.utcnow()+timedelta(minutes=45)
    def with_quota_project(self,quota_project_id): return self

def setup():
    from app.core.config import settings
    from app.services import store
    from app.services.auth import User,current_user
    credentials=GcloudCredentials();credentials.refresh(None)
    config=json.loads(subprocess.check_output(['gcloud','run','services','describe','city-rag-backend-dev','--account='+ACCOUNT,'--project='+PROJECT,'--region=asia-east1','--format=json'],text=True))
    for item in config['spec']['template']['spec']['containers'][0]['env']:
        if 'valueFrom' in item: continue
        name,value=item['name'],item.get('value','')
        if not hasattr(settings,name):continue
        old=getattr(settings,name)
        if isinstance(old,bool):value=value.lower()=='true'
        elif isinstance(old,(list,dict)):value=json.loads(value)
        elif isinstance(old,int):value=int(value)
        elif isinstance(old,float):value=float(value)
        setattr(settings,name,value)
    headers={'Authorization':'Bearer '+credentials.token}
    response=requests.get('https://openidconnect.googleapis.com/v1/userinfo',headers=headers,timeout=30);response.raise_for_status()
    info=response.json();assert info['email']==ACCOUNT and info['email_verified']
    current_user.set(User(info['sub'],info['email']))
    response=requests.get(f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets/city-governance-database-url/versions/latest:access',headers=headers,timeout=30);response.raise_for_status()
    url=make_url(base64.b64decode(response.json()['payload']['data']).decode())
    instance=url.query.get('host',url.host or '').removeprefix('/cloudsql/')
    assert instance=='tdf-ocf:asia-east1:city-governance-postgres', 'Unexpected database instance'
    settings.DATABASE_URL=url.set(host='127.0.0.1',port=54329,query={}).render_as_string(hide_password=False)
    store.engine.cache_clear()
    google.auth.default=lambda **kwargs:(credentials,PROJECT)
    from app.services import cloud
    cloud.default=lambda **kwargs:(credentials,PROJECT)
    return credentials,instance
