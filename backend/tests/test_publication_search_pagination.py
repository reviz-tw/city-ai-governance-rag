import json

from app.services import chunks, store
from test_publication import start


def test_repeated_ranked_results_recover_missing_chunks_with_exact_filters(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    with store.session() as db:
        publication = db.get(store.Publication, doc.id + ':1')
    publication.chunks = [{**doc.draft[0], 'id': f'c{i}', 'order': i,
                           'content': f'Original passage {i}'} for i in range(3)]
    records = chunks.manifest(doc, publication, 'gs://original/file.pdf')
    calls = []

    def request(path, payload, method):
        calls.append(payload)
        assert publication.index_document_id in payload['filter']
        if 'chunk_id: ANY(' in payload['filter']:
            assert payload['filter'].endswith('chunk_id: ANY("c2")')
            return {'results': [{'document': records[2]}]}
        if not payload['pageToken']:
            return {'results': [{'document': records[0]}, {'document': records[1]}],
                    'nextPageToken': 'second-page'}
        return {'results': [{'document': records[1]}]}

    monkeypatch.setattr(chunks.cloud, 'request', request)
    remote = chunks.search_publication(publication)
    assert len(calls) == 3 and chunks.matches(publication, remote)
    remote[records[2]['id']]['structData']['content_sha256'] = 'incorrect'
    assert not chunks.matches(publication, remote)


def test_exact_lookup_does_not_accept_a_genuinely_missing_chunk(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    with store.session() as db:
        publication = db.get(store.Publication, doc.id + ':1')
    calls = []

    def request(path, payload, method):
        calls.append(payload)
        return {'results': []}

    monkeypatch.setattr(chunks.cloud, 'request', request)
    remote = chunks.search_publication(publication)
    assert not chunks.matches(publication, remote)
    assert 'chunk_id: ANY(' in calls[-1]['filter']


def test_missing_chunk_lookups_use_bounded_filters(source, monkeypatch):
    doc, task = start(source, monkeypatch)
    with store.session() as db:
        publication = db.get(store.Publication, doc.id + ':1')
    publication.chunks = [{**doc.draft[0], 'id': f'c{i}', 'order': i,
                           'content': f'Original passage {i}'} for i in range(205)]
    records = chunks.manifest(doc, publication, 'gs://original/file.pdf')
    by_id = {r['structData']['chunk_id']: r for r in records}
    lengths = []

    def request(path, payload, method):
        if 'chunk_id: ANY(' not in payload['filter']:
            return {'results': []}
        expression = payload['filter'].split('chunk_id: ANY(', 1)[1][:-1]
        selected = json.loads('[' + expression + ']')
        lengths.append(len(selected))
        return {'results': [{'document': by_id[i]} for i in selected]}

    monkeypatch.setattr(chunks.cloud, 'request', request)
    assert chunks.matches(publication, chunks.search_publication(publication))
    assert lengths == [100, 100, 5]
