"""Use the existing dev database through Cloud SQL Proxy without saving secrets."""
import base64
import json
import subprocess
import urllib.request
from google.oauth2.credentials import Credentials
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.services import store


def connect():
    access = subprocess.check_output(['gcloud','auth','print-access-token','--account=hcchien@reviz.tw'],text=True).strip()
    request = urllib.request.Request('https://secretmanager.googleapis.com/v1/projects/tdf-ocf/secrets/city-governance-database-url/versions/latest:access',
                                     headers={'Authorization':'Bearer '+access})
    with urllib.request.urlopen(request,timeout=30) as response:
        value = base64.b64decode(json.load(response)['payload']['data']).decode()
    settings.DATABASE_URL = make_url(value).set(host='127.0.0.1',port=54329,query={}).render_as_string(hide_password=False)
    store.engine.cache_clear()
    credential = Credentials(access)
    return credential
