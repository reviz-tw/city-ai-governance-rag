"""Plan or rerun Docling drafts for sources without any human review.

Connect using the operator's existing IAM identity. Credentials remain in memory.
Run from the checkout with PYTHONPATH=backend. Never publishes or marks reviewed.
"""
import argparse
import json
from pathlib import Path
from sqlalchemy import select
from app.services import store, rechunk
from app.services.auth import require_editor


def run(report:Path,apply:bool,only:list[str],workers=1,enqueue=False):
    user=require_editor()
    if not user.admin:raise RuntimeError('Administrator required for batch rechunking')
    ids=rechunk.eligible_ids()
    if only:ids=[i for i in ids if i in only]
    results=[]
    if not apply and not enqueue:
        with store.session() as db:
            rows=db.execute(select(store.Document.id,store.Document.title,store.Document.draft_revision,
                store.Document.published_version,store.Document.original_hash,
                store.Document.draft).where(store.Document.id.in_(ids)).order_by(store.Document.id))
            results=[dict(id=i,title=t,revision=r,published_version=v,original_hash=h,
                old_chunks=len(c),status='eligible') for i,t,r,v,h,c in rows]
        report.write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps({'eligible':len(results),'report':str(report)}),flush=True)
        return results
    def process(identifier):
        with store.session() as db:
            doc=db.get(store.Document,identifier)
            row=dict(id=doc.id,title=doc.title,revision=doc.draft_revision,published_version=doc.published_version,
                original_hash=doc.original_hash,old_chunks=len(doc.draft))
        try:
            if enqueue:
                with store.session() as db:
                    applied=db.scalar(select(store.DoclingProposal).where(store.DoclingProposal.document_id==doc.id,
                        store.DoclingProposal.status=='applied').order_by(store.DoclingProposal.created_at.desc()))
                    ready=db.scalar(select(store.DoclingProposal).where(store.DoclingProposal.document_id==doc.id,
                        store.DoclingProposal.status=='ready',store.DoclingProposal.base_revision==doc.draft_revision,
                        store.DoclingProposal.original_hash==doc.original_hash))
                    updated=applied and applied.original_hash==doc.original_hash and applied.chunks==doc.draft
                if updated:row['status']='already-updated'
                elif ready:row.update(rechunk.apply(identifier,ready.id,row['revision'],preserve_manual=True))
                else:
                    job=rechunk.enqueue(identifier,row['revision'],apply_unreviewed=True)
                    row.update(status=job['status'],job_id=job['id'])
            else:
                proposed=rechunk.generate(identifier)
                row.update(proposal=proposed)
                row.update({'status':'already-updated'} if proposed['status']=='already-updated' else rechunk.apply(identifier,proposed['id'],row['revision'],preserve_manual=True))
            with store.session() as db:
                current=db.get(store.Document,identifier)
                assert current.published_version==row['published_version']
                assert current.original_hash==row['original_hash']
                if row['status']=='applied':
                    assert current.draft_revision==row['revision']
                    assert all(c['algorithm']=='docling-hybrid-v1' for c in current.draft)
        except Exception as exc:
            row.update(status='failed',error=getattr(exc,'detail',type(exc).__name__))
        return row
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from contextvars import copy_context
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures=[executor.submit(copy_context().run,process,identifier) for identifier in ids]
        for future in as_completed(futures):
            row=future.result()
            results.append(row)
            report.write_text(json.dumps(results,ensure_ascii=False,indent=2))
            print(json.dumps(row,ensure_ascii=False),flush=True)
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--apply',action='store_true')
    action.add_argument('--enqueue',action='store_true',help='Process through deployed Cloud Tasks and apply safe drafts')
    parser.add_argument('--cloud',action='store_true')
    parser.add_argument('--workers',type=int,choices=range(1,5),default=1)
    parser.add_argument('--only',action='append',default=[])
    parser.add_argument('--report',type=Path,default=Path('/tmp/city-docling-rechunk-report.json'))
    args=parser.parse_args()
    proxy=None
    try:
        if args.cloud:
            # Reuse existing verified identity/config loading without changing account or project.
            import importlib.util,os,subprocess,socket,time
            source=Path(__file__).resolve().parents[2]/'data/imports/13c88uASCEmKJkBWnGNi8aJB9ETCZxlRm/cloud_access.py'
            spec=importlib.util.spec_from_file_location('cloud_access',source)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            credentials,instance=module.setup()
            with socket.socket() as available:
                available.bind(('127.0.0.1',0));port=available.getsockname()[1]
            from sqlalchemy.engine import make_url
            from app.core.config import settings
            if os.environ.get('DOCLING_PYTHON'):
                settings.DOCLING_SERVICE_URL=''
            settings.DATABASE_URL=make_url(settings.DATABASE_URL).set(port=port).render_as_string(hide_password=False)
            store.engine.cache_clear()
            proxy=subprocess.Popen(['cloud-sql-proxy',instance,f'--port={port}','--address=127.0.0.1','--gcloud-auth'],
                env={**os.environ,'CLOUDSDK_CORE_ACCOUNT':module.ACCOUNT},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(60):
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=1):break
                except OSError:time.sleep(0.5)
            # Proposal auditing and operator authorization; no conversation migration here.
            store.DoclingProposal.__table__.create(store.engine(),checkfirst=True)
            store.WorkspaceAccount.__table__.create(store.engine(),checkfirst=True)
            store.AccountInitialization.__table__.create(store.engine(),checkfirst=True)
            from app.services.accounts import bootstrap
            bootstrap()
        run(args.report,args.apply,args.only,args.workers,args.enqueue)
    finally:
        if proxy:proxy.terminate();proxy.wait(timeout=10)
