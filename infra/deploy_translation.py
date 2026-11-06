"""Deploy pinned TranslateGemma job or verified web revision; run from repository root.

Build first: gcloud builds submit --config=infra/cloudbuild.translation.yaml --substitutions=_TAG=TAG
This script reuses the existing runtime identity and does not change IAM.
"""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['job', 'queue', 'sample', 'backfill', 'status', 'web'])
parser.add_argument('--tag', required=True)
parser.add_argument('--project', default='tdf-ocf')
parser.add_argument('--gpu-region', default='asia-southeast1')
args = parser.parse_args()
project = args.project
service = 'city-rag-backend-dev'
job = 'city-translategemma'
registry = f'asia-east1-docker.pkg.dev/{project}/haystack-dev'


def run(*parts, capture=False):
    command = ['gcloud', *parts, '--project', project, '--quiet']
    if capture:
        return subprocess.check_output(command, text=True).strip()
    subprocess.run(command, check=True)


if args.action in {'job', 'queue'}:
    identity = run('run', 'services', 'describe', service, '--region=asia-east1',
                   '--format=value(spec.template.spec.serviceAccountName)', capture=True)
    if not identity:
        raise SystemExit('Existing service has no explicit runtime service account')
    image_name = job if args.action == 'job' else service
    digest = run('artifacts', 'docker', 'images', 'describe', f'{registry}/{image_name}:{args.tag}',
                 '--format=value(image_summary.digest)', capture=True)
    if not digest.startswith('sha256:'):
        raise SystemExit('Worker image digest not found')
    name = job if args.action == 'job' else job+'-queue'
    region = args.gpu_region if args.action == 'job' else 'asia-east1'
    resources = ['--gpu=1', '--gpu-type=nvidia-l4', '--no-gpu-zonal-redundancy',
                 '--cpu=4', '--memory=16Gi', '--task-timeout=900s',
                 '--args=--max-seconds,720'] if args.action == 'job' else [
                 '--cpu=1', '--memory=1Gi', '--task-timeout=300s', '--command=python',
                 '--args=-m,app.translation_worker,--backfill,--queue-only']
    run('run', 'jobs', 'deploy', name, '--region', region,
        '--image', f'{registry}/{image_name}@{digest}', *resources,
        '--tasks=1', '--parallelism=1', '--max-retries=0', '--service-account', identity,
        '--env-vars-file=infra/env.dev.yaml',
        '--set-secrets=DATABASE_URL=city-governance-database-url:latest',
        f'--set-cloudsql-instances={project}:asia-east1:city-governance-postgres')
    if args.action == 'queue':
        run('run', 'jobs', 'execute', name, '--region', region, '--async')
elif args.action in {'sample', 'backfill', 'status'}:
    name = job+'-queue' if args.action == 'status' else job
    region = 'asia-east1' if args.action == 'status' else args.gpu_region
    executions = json.loads(run('run', 'jobs', 'executions', 'list', '--job', name,
                                '--region', region, '--format=json', capture=True))
    if any(not item.get('status', {}).get('completionTime') for item in executions):
        raise SystemExit('An execution is still active; refusing another GPU allocation')
    flags = {'sample': '--limit,12,--max-seconds,600',
             'backfill': '--max-seconds,720', 'status': '-m,app.translation_worker,--status'}
    run('run', 'jobs', 'execute', name, '--region', region,
        '--args='+flags[args.action], '--async')
else:
    # Preserve all existing environment, secret, scaling, and IAM settings.
    env = json.loads(subprocess.check_output(['python3', '-c',
        'import yaml,json; print(json.dumps(yaml.safe_load(open("infra/env.dev.yaml"))))'], text=True))
    updates = ','.join(f'{key}={value}' for key, value in env.items()
                       if key.startswith('TRANSLATION_') and key != 'TRANSLATION_LANGUAGES')
    revision = f'{service}-{args.tag}'
    run('run', 'deploy', service, '--region=asia-east1',
        '--image', f'{registry}/{service}:{args.tag}', '--no-traffic', '--tag=candidate',
        '--revision-suffix', args.tag, '--update-env-vars', updates)
    subprocess.run(['python3', 'infra/verify_deployment.py', service, 'asia-east1', project,
                    revision, 'https://city-rag-backend-dev-wvswpuk2tq-de.a.run.app'], check=True)
