"""Deploy a hashed source overlay on the existing immutable model image.

Avoid rebuilding/retransferring model weights for operator diagnostics. No model
download, package installation, IAM change or execution happens during deployment.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

FILES = ['services/translation_numbers.py', 'services/store.py', 'services/translations.py', 'services/local_translation.py',
         'services/ollama_translation.py', 'translation_worker.py']
BASE = ('asia-east1-docker.pkg.dev/tdf-ocf/haystack-dev/city-translategemma@'
        'sha256:7e8d3b8538acf793bf97ad2887faeb2eb1383a629c5f1cac59b221b3c5c8c87c')


def bootstrap(language, diagnostics=0):
    payload = json.dumps({name:Path('backend/app', name).read_text() for name in FILES},
                         sort_keys=True).encode()
    digest = hashlib.sha256(payload).hexdigest()
    blob = base64.b64encode(gzip.compress(payload, mtime=0)).decode()
    code = ("import base64,gzip,hashlib,json,pathlib,os; "
            f"p=gzip.decompress(base64.b64decode('{blob}')); "
            f"assert hashlib.sha256(p).hexdigest()=='{digest}'; "
            "files=json.loads(p); "
            f"assert set(files)==set({FILES!r}); "
            "[(pathlib.Path('/app/app')/name).write_text(text) for name,text in files.items()]; "
            f"print('translation_source_sha256={digest}',flush=True); "
            "os.execv('/bin/sh',['sh','/app/translation-entrypoint.sh',"
            f"'--language','{language}','--max-seconds','720','--diagnostics-limit','{diagnostics}'])")
    if len(code.encode()) > 30000:
        raise ValueError('Source overlay exceeds the bounded command payload')
    return digest, code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--language', choices=['en'], default='en')
    p.add_argument('--diagnostics', type=int, choices=range(51), default=50)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--tasks',type=int,choices=range(1,181),default=1,
                   help='Finite tasks, sequential, each capped at 900 seconds; max 45 GPU hours')
    args = p.parse_args()
    common = ['--project=tdf-ocf', '--region=asia-southeast1', '--quiet']
    def run(parts, capture=False):
        return subprocess.check_output(['gcloud',*parts,*common],text=True) if capture else subprocess.run(['gcloud',*parts,*common],check=True)
    runs = json.loads(run(['run','jobs','executions','list','--job=city-translategemma','--format=json'], True))
    if any(not r.get('status',{}).get('completionTime') for r in runs):
        raise SystemExit('An execution is active; refusing to update/start another')
    digest, code = bootstrap(args.language,args.diagnostics)
    run(['run','jobs','update','city-translategemma','--image='+BASE,
         '--command=python','--args=^~^-c~'+code,'--task-timeout=900s',
         f'--tasks={args.tasks}','--parallelism=1','--max-retries=0'])
    print(json.dumps({'source_sha256':digest,'language':args.language,
                      'timeout_seconds':900,'tasks':args.tasks,
                      'max_gpu_hours':args.tasks/4,
                      'max_list_compute_usd':round(args.tasks/4*1.255824,2),
                      'diagnostics_limit':args.diagnostics}),flush=True)
    if args.execute:
        run(['run','jobs','execute','city-translategemma','--async'])


if __name__ == '__main__':
    main()
