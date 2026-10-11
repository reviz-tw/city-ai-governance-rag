"""Single-attempt sequential rechunk execution outside HTTP task deadlines."""
import logging
import time
from sqlalchemy import select,text
from app.core.config import settings
from app.services import jobs,store
logger=logging.getLogger(__name__)


def launch():
    from google.auth import default
    from google.auth.transport.requests import AuthorizedSession
    credentials,_=default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    name=f'projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}/jobs/{settings.DOCLING_RUN_JOB}'
    with AuthorizedSession(credentials) as client:
        response=client.post(f'https://run.googleapis.com/v2/{name}:run',json={},timeout=30)
        response.raise_for_status()


def drain():
    # Session-level lock prevents duplicate launches from parsing in parallel.
    with store.engine().connect() as lock:
        if not lock.scalar(text('SELECT pg_try_advisory_lock(734196028)')):
            logger.info('docling_batch_already_running')
            return
        try:
            while True:
                with store.session() as db:
                    identifier=db.scalar(select(store.Job.id).where(
                        store.Job.kind=='rechunk',store.Job.status=='queued',
                        store.Job.expires_at>time.time()).order_by(store.Job.created_at).limit(1))
                if identifier is None:return
                logger.info('docling_batch_job_started id=%s',identifier)
                jobs.run(identifier)
                with store.session() as db:
                    job=db.get(store.Job,identifier)
                    logger.info('docling_batch_job_finished id=%s status=%s',identifier,job.status if job else 'removed')
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(734196028)'))


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    drain()
