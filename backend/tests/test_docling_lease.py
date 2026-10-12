from app.core.config import settings
from app.services.docling_lease import CallerLease


def test_transport_failure_waits_for_worker_stop_ack(monkeypatch):
    from google.cloud import storage
    monkeypatch.setattr(settings,'ARTIFACT_GCS_BUCKET','test-artifacts')
    events=[];polls=[]
    class Blob:
        def __init__(self,key):self.key=key
        def upload_from_string(self,*args,**kwargs):events.append('renew')
        def delete(self,**kwargs):events.append('delete-ack' if '.stopped.' in self.key else 'revoke')
        def exists(self,**kwargs):polls.append(1);return len(polls)==2
    class Client:
        def __init__(self,**kwargs):pass
        def bucket(self,name):return self
        def blob(self,key):return Blob(key)
    monkeypatch.setattr(storage,'Client',Client)
    monkeypatch.setattr('app.services.docling_lease.time.sleep',lambda _:events.append('wait'))
    lease=CallerLease();lease.close(completed=False)
    assert events==['renew','revoke','wait','delete-ack']
    assert len(polls)==2
