"""Cloud Tasks keeps deployed jobs alive independently of browser requests and worker instances."""
import base64
from datetime import datetime, timezone
from app.core.config import settings


def enqueue(job):
    if not settings.CLOUD_TASKS_QUEUE:
        return
    from google.auth import default
    from google.auth.transport.requests import AuthorizedSession
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'], quota_project_id=settings.GCP_PROJECT_ID)
    parent = f'projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}/queues/{settings.CLOUD_TASKS_QUEUE}'
    task = {'httpRequest':{'httpMethod':'POST','url':f'{settings.APP_ORIGIN}/internal/jobs/{job.id}',
                          'headers':{'Content-Type':'application/json'}, 'body':base64.b64encode(b'{}').decode(),
                          'oidcToken':{'serviceAccountEmail':settings.WORKER_SERVICE_ACCOUNT,'audience':settings.APP_ORIGIN}},
            'dispatchDeadline':'1800s'}
    if job.payload.get('resume_at'):
        task['scheduleTime']=datetime.fromtimestamp(job.payload['resume_at'],timezone.utc).isoformat()
    with AuthorizedSession(credentials) as client:
        response=client.post(f'https://cloudtasks.googleapis.com/v2/{parent}/tasks',json={'task':task},timeout=30)
        if response.status_code >= 400:
            raise RuntimeError('Background task dispatch failed')
