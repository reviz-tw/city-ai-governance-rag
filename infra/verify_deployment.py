"""Check the candidate and promote the exact build revision on the existing service."""
import json
import subprocess
import sys
import urllib.request
import urllib.error

service, region, project, revision, expected_url = sys.argv[1:]


def describe():
    return json.loads(subprocess.check_output([
        'gcloud', 'run', 'services', 'describe', service, '--region', region,
        '--project', project, '--format=json'], text=True))


def check_identity(state):
    if state['status']['url'] != expected_url:
        raise SystemExit('Service URL changed; refusing promotion')
    if state['status']['latestCreatedRevisionName'] != revision:
        raise SystemExit('A newer deployment exists; refusing to promote an older build')


state = describe()
check_identity(state)
candidate = next(t['url'] for t in state['status']['traffic']
                 if t.get('tag') == 'candidate' and t.get('revisionName') == revision)
for path in ['/api/health', '/api/auth/config', '/admin/']:
    with urllib.request.urlopen(candidate + path, timeout=60) as response:
        body = response.read().decode()
        if path == '/admin/' and '/assets/' not in body:
            raise SystemExit('Admin route did not serve the authenticated application')
        if path == '/api/health' and json.loads(body).get('status') != 'ok':
            raise SystemExit('Candidate health check failed')
try:
    urllib.request.urlopen(candidate + '/api/library', timeout=60)
except urllib.error.HTTPError as error:
    if error.code != 401:
        raise
else:
    raise SystemExit('Document library must require authentication')
check_identity(describe())
subprocess.run(['gcloud', 'run', 'services', 'update-traffic', service, '--region', region,
                '--project', project, '--to-revisions', revision + '=100', '--quiet'], check=True)
state = describe()
check_identity(state)
if not any(t.get('revisionName') == revision and t.get('percent') == 100 for t in state['status']['traffic']):
    raise SystemExit('The verified revision is not serving all traffic')
print('Verified deployment on the unchanged service URL: ' + expected_url)
