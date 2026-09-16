"""Authenticated provider calls with bounded error messages and no credential logging."""
from google.auth import default
from google.auth.transport.requests import AuthorizedSession
from app.core.config import settings


def request(path, payload=None, method='GET'):
    credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'], quota_project_id=settings.GCP_PROJECT_ID)
    with AuthorizedSession(credentials) as client:
        result = client.request(method, 'https://discoveryengine.googleapis.com/v1alpha/' + path,
                                json=payload, timeout=120)
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
