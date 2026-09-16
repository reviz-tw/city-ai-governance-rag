"""Synthetic end-to-end SDK smoke; never transmits stored research documents."""
import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from google import genai
from google.oauth2.credentials import Credentials
from app.core.config import settings
from app.services import gemini, store, documents, jobs
from app.services.auth import User, current_user
from app.pipelines import vertex_search as rag
from app.pipelines.cleaner import clean_and_annotate_document
from app.models.artifacts import ArtifactRequest

@contextmanager
def authenticated_client():
    token=subprocess.run(['gcloud','auth','print-access-token','--account','hcchien@reviz.tw'],check=True,capture_output=True,text=True).stdout.strip()
    with genai.Client(vertexai=True,project='tdf-ocf',location='global',credentials=Credentials(token=token),http_options={'timeout':120000}) as client:
        yield client

def main():
    gemini.client=authenticated_client
    original_generate=gemini.generate
    def checked_generate(*args, **kwargs):
        try:
            return original_generate(*args, **kwargs)
        except Exception as exc:
            if hasattr(exc, 'errors'):
                print(json.dumps(exc.errors(include_input=False, include_url=False)),flush=True)
            raise
    gemini.generate=checked_generate
    settings.DATABASE_URL='sqlite:////tmp/city-governance-sdk-smoke.db'
    settings.ARTIFACT_STORAGE_DIR='/tmp/city-governance-sdk-artifacts'
    settings.EDITOR_EMAILS=['editor@example.test']
    settings.SOFFICE_BIN='/Users/hcchien/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice'
    store.initialize()
    current_user.set(User('smoke','editor@example.test'))
    content='Synthetic policy for testing only. In 2026, 20 cases required human review. Automatic approval is prohibited. City staff must assess privacy risk.'
    source=documents.create(content.encode(),'synthetic-smoke.txt','text/plain',{'language':'en'})
    def retrieve(*args):
        return [{'id':source['id'],'title':'Synthetic test policy','snippets':[{'snippet':content}], 'metadata':{'language':'en','document_id':source['id'],'version':source['original_hash']}}]
    rag.retrieve=retrieve
    report={}
    for language,question in [('zh-TW','這份合成測試政策要求人工審查幾件案件？'),('ja','この合成テスト方針では、何件の案件に人による確認が必要ですか？')]:
        response=rag.query_city_governance_rag_vertex(question, interface_language='en')
        report[language]={'language':response['response_language'],'status':response['status'],'answer':response['answer'],'citations':[s['citation_id'] for s in response['sources']]}
    events=[json.loads(frame.removeprefix('data: ')) for frame in rag.stream_city_governance_rag_vertex('What does this synthetic policy prohibit?')]
    report['stream']={'types':[e['type'] for e in events],'answer':''.join(e.get('text','') for e in events),'done':events[-1]}
    cleaned=clean_and_annotate_document(content,'synthetic-smoke.txt')
    report['cleaner']={'language':cleaned.suggested_metadata.language,'summary':cleaned.summary}
    for kind in ['pdf','pptx','chart','translation']:
        request=ArtifactRequest(kind=kind,scope='document' if kind=='translation' else 'answer',message_ids=['synthetic-message'], source_ids=[source['id']],language='ja' if kind=='translation' else 'zh-TW',pages=6)
        task=jobs.create(request);jobs.run(task['id']);job=jobs.get(task['id'])
        if job.status=='awaiting_review':
            jobs.mutate(job.id,'confirm',job.revision,job.draft);jobs.run(job.id);job=jobs.get(job.id)
        report[kind]={'id':job.id,'status':job.status,'error':job.error,'files':job.result,'draft':job.draft}
        print(json.dumps({'kind':kind,'status':job.status,'error':job.error}),flush=True)
    Path('/tmp/city-governance-sdk-smoke-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:({x:y for x,y in v.items() if x not in {'draft','files'}}) for k,v in report.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
