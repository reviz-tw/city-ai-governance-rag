"""One-time dev bootstrap. Secret values stay in memory and Secret Manager.

Run only after the approved Cloud SQL instance is RUNNABLE. This intentionally
refuses to overwrite existing credentials; rotation is a separate operation.
"""
import base64
import json
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

PROJECT = 'tdf-ocf'
INSTANCE = 'city-governance-postgres'
RUNTIME = '59297909591-compute@developer.gserviceaccount.com'
access = subprocess.run(['gcloud', 'auth', 'print-access-token', '--account=hcchien@reviz.tw'],
                        check=True, capture_output=True, text=True).stdout.strip()

def call(host, path, body=None, method=None, allow_missing=False):
    request = urllib.request.Request('https://' + host + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + access, 'Content-Type': 'application/json'}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if allow_missing and exc.code == 404:
            return None
        # Do not echo response bodies or submitted credential values.
        raise RuntimeError(f'{host} request failed: HTTP {exc.code}') from None

sql_path = f'/sql/v1beta4/projects/{PROJECT}/instances/{INSTANCE}'
instance = call('sqladmin.googleapis.com', sql_path)
if instance['state'] != 'RUNNABLE':
    raise SystemExit('Database is not ready; rerun after creation completes.')
secret_root = f'/v1/projects/{PROJECT}/secrets'
names = ['city-governance-session', 'city-governance-database-url']
for name in names:
    if call('secretmanager.googleapis.com', secret_root + '/' + name, allow_missing=True):
        raise SystemExit('Existing secret found; refusing to overwrite credentials.')
def wait_sql(operation):
    for _ in range(90):
        status = call('sqladmin.googleapis.com', f'/sql/v1beta4/projects/{PROJECT}/operations/' + operation['name'])
        if status['status'] == 'DONE':
            if status.get('error'):
                raise RuntimeError('Database setup operation failed')
            return
        time.sleep(2)
    raise RuntimeError('Database operation is still pending')

users = call('sqladmin.googleapis.com', sql_path + '/users')
if any(user['name'] == 'city_governance_app' for user in users.get('items', [])):
    raise SystemExit('Application database user already exists; refusing to rotate implicitly.')
databases = call('sqladmin.googleapis.com', sql_path + '/databases')
if not any(db['name'] == 'city_governance' for db in databases.get('items', [])):
    wait_sql(call('sqladmin.googleapis.com', sql_path + '/databases', {'name': 'city_governance'}, 'POST'))
password = secrets.token_urlsafe(40)
wait_sql(call('sqladmin.googleapis.com', sql_path + '/users',
     {'name': 'city_governance_app', 'password': password, 'type': 'BUILT_IN'}, 'POST'))
database_url = ('postgresql+psycopg://city_governance_app:' + urllib.parse.quote(password, safe='') +
                '@/city_governance?host=/cloudsql/tdf-ocf:asia-east1:' + INSTANCE)
for name, value in zip(names, [secrets.token_urlsafe(64), database_url]):
    call('secretmanager.googleapis.com', secret_root + '?secretId=' + name,
         {'replication': {'userManaged': {'replicas': [{'location': 'asia-east1'}]}}}, 'POST')
    call('secretmanager.googleapis.com', secret_root + '/' + name + ':addVersion',
         {'payload': {'data': base64.b64encode(value.encode()).decode()}}, 'POST')
    call('secretmanager.googleapis.com', secret_root + '/' + name + ':setIamPolicy',
         {'policy': {'bindings': [{'role': 'roles/secretmanager.secretAccessor',
                                   'members': ['serviceAccount:' + RUNTIME]}]}}, 'POST')
    print(name + ': created version 1 and granted runtime read access', flush=True)
print('Dedicated database/user and credentials created; no secret values written to files.')
