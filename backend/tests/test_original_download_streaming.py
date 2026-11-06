import asyncio
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import unquote

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.api import workspace


def test_large_original_uses_chunked_response_and_preserves_exact_bytes(monkeypatch):
    data = b'%PDF-1.6\n' + b'x' * (33 * 1024 * 1024) + b'\n%%EOF'
    key = 'managed-originals/doc/1130828-臺北智慧城市對外簡報(TPMO).pdf'
    getter = Mock(return_value=SimpleNamespace(original_key=key, mime='application/pdf'))
    monkeypatch.setattr(workspace.documents, 'get', getter)
    monkeypatch.setattr(workspace.store, 'get_bytes', lambda requested: data if requested == key else None)
    response = workspace.original('doc')
    getter.assert_called_once_with('doc')
    assert isinstance(response, StreamingResponse)
    assert 'content-length' not in response.headers
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert unquote(response.headers['content-disposition'].split("UTF-8''")[1]) == key.rsplit('/', 1)[1]

    async def consume():
        digest = hashlib.sha256()
        total = 0
        count = 0
        async for piece in response.body_iterator:
            assert 0 < len(piece) <= 1024 * 1024
            digest.update(piece)
            total += len(piece)
            count += 1
        return digest.hexdigest(), total, count

    digest, total, count = asyncio.run(consume())
    assert digest == hashlib.sha256(data).hexdigest() and total == len(data)
    assert count > 32


def test_original_download_checks_access_before_reading_source(monkeypatch):
    getter = Mock(side_effect=HTTPException(404, 'Document not found'))
    reader = Mock()
    monkeypatch.setattr(workspace.documents, 'get', getter)
    monkeypatch.setattr(workspace.store, 'get_bytes', reader)
    with pytest.raises(HTTPException) as error:
        workspace.original('private-document')
    assert error.value.status_code == 404
    reader.assert_not_called()
