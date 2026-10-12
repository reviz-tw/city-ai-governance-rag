"""Revoke parsing on transport failure and wait for worker process-stop acknowledgement."""
import time
import uuid
from app.core.config import settings
from app.services import store


class CallerLease:
    def __init__(self):
        self.id=uuid.uuid4().hex
        self.key=f'docling-leases/{self.id}.json'
        self.stopped_key=f'docling-leases/{self.id}.stopped.json'
        self.last_update=0
        self.renew()

    def renew(self):
        if time.monotonic()-self.last_update<10:return
        if settings.ARTIFACT_GCS_BUCKET:
            from google.cloud import storage
            storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(self.key).upload_from_string('{}',content_type='application/json',timeout=10,retry=None)
        else:store.put_bytes(self.key,b'{}','application/json')
        self.last_update=time.monotonic()

    def delete(self,key):
        if settings.ARTIFACT_GCS_BUCKET:
            from google.cloud import storage
            storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(key).delete(timeout=10,retry=None)
        else:store.delete_bytes(key)

    def close(self, *, completed):
        try:self.delete(self.key)
        except Exception:pass # Lease expiry still stops parsing when deletion cannot reach storage.
        if not completed and settings.ARTIFACT_GCS_BUCKET:
            from google.cloud import storage
            blob=storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.ARTIFACT_GCS_BUCKET).blob(self.stopped_key)
            deadline=time.monotonic()+75
            while time.monotonic()<deadline:
                try:
                    if blob.exists(timeout=5,retry=None):break
                except Exception:pass
                time.sleep(2)
            else:
                import logging
                logging.getLogger(__name__).warning('docling_cleanup_ack_missing lease=%s',self.id)
                return
        try:self.delete(self.stopped_key)
        except Exception:pass
