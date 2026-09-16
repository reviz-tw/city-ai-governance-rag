"""Authenticated provider calls with bounded error messages and no credential logging."""
from google.auth import default
from google.auth.transport.requests import AuthorizedSession
from app.core.config import settings


class IndexNotReady(RuntimeError):
    """Retryable provider indexing or schema propagation delay."""


def request(path, payload=None, method='GET', *, allow_missing=False):
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'], quota_project_id=settings.GCP_PROJECT_ID)
    with AuthorizedSession(credentials) as client:
        result = client.request(method, 'https://discoveryengine.googleapis.com/v1/' + path,
                                json=payload, timeout=120)
        if result.status_code == 404 and allow_missing:
            return None
        if result.status_code in {429, 500, 502, 503, 504}:
            raise IndexNotReady('Search service temporarily unavailable')
        if result.status_code == 400 and path.endswith(':search'):
            message=result.json().get('error',{}).get('message','')
            if 'Unsupported field' in message and 'filter' in message.lower():
                raise IndexNotReady('Search metadata is still being indexed')
        if result.status_code >= 400:
            raise RuntimeError(f'Discovery Engine request failed ({result.status_code})')
        return result.json() if result.content else {}


def store_path():
    return (f'projects/{settings.GCP_PROJECT_ID}/locations/{settings.VERTEX_LOCATION}/'
            f'collections/default_collection/dataStores/{settings.CHUNK_DATA_STORE_ID}')


def search_path():
    if settings.CHUNK_SEARCH_ENGINE_ID:
        return (f'projects/{settings.GCP_PROJECT_ID}/locations/{settings.VERTEX_LOCATION}/'
                f'collections/default_collection/engines/{settings.CHUNK_SEARCH_ENGINE_ID}/servingConfigs/default_search:search')
    return store_path()+'/servingConfigs/default_search:search'
