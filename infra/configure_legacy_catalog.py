"""Administrator bootstrap: create/update the private hourly catalogue trigger.

Run separately from Cloud Build; do not broaden the build service account roles.
"""
import json
import subprocess
import sys

project, region, service_account = sys.argv[1:]
job = 'city-legacy-catalog'
base = ['gcloud','scheduler','jobs']
lookup = subprocess.run(base+['list','--project='+project,'--location='+region,'--format=json'],stdout=subprocess.PIPE,text=True,check=True)
exists = any(item['name'].endswith('/'+job) for item in json.loads(lookup.stdout))
subprocess.run(base+['update' if exists else 'create','http',job,
    '--project='+project,'--location='+region,'--schedule=15 * * * *','--time-zone=Etc/UTC',
    '--uri=https://run.googleapis.com/v2/projects/'+project+'/locations/'+region+'/jobs/'+job+':run',
    '--http-method=POST','--headers=Content-Type=application/json','--message-body={}',
    '--oauth-service-account-email='+service_account,
    '--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform',
    '--attempt-deadline=60s'],check=True)
