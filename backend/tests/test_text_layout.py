import re
from copy import deepcopy
from unittest.mock import Mock

import pytest

from app.services import chunks, documents, store
from app.services.text_layout import reflow


@pytest.mark.parametrize(('source', 'expected'), [
    ('機關導入人工智慧時，\n    應先評估隱私與安全風險。', '機關導入人工智慧時，應先評估隱私與安全風險。'),
    ('The city should assess privacy risks before\nusing any automated decision system.', 'The city should assess privacy risks before using any automated decision system.'),
    ('Use risk-\nbased review.', 'Use risk-based review.'),
    ('機關導入人工智慧時，\r\n應先評估風險。\r\n\r\n\r\n另訂作業規範。', '機關導入人工智慧時，應先評估風險。\n\n另訂作業規範。'),
    ('一、使用原則\n機關導入人工智慧時，\n應先評估風險。\n二、人工覆核\n不得自動批准。', '一、使用原則\n機關導入人工智慧時，應先評估風險。\n二、人工覆核\n不得自動批准。'),
    ('# Heading\n1. Scope\n2. Review\n- First item\n- Second item', '# Heading\n1. Scope\n2. Review\n- First item\n- Second item'),
    ('第 1 段：合成資料\n機關導入人工智慧時，\n應先評估風險。', '第 1 段：合成資料\n機關導入人工智慧時，應先評估風險。'),
    ('This is a complete sentence.\nThis is another sentence.', 'This is a complete sentence.\nThis is another sentence.'),
    ('機關  件數\n甲市  20\n乙市  30', '機關  件數\n甲市  20\n乙市  30'),
    ('City\tCases\nA\t20\nB\t30', 'City\tCases\nA\t20\nB\t30'),
    ('| City | Cases |\n| A | 20 |', '| City | Cases |\n| A | 20 |'),
    ('```python\nfor item in items:\n    print(item)\n```', '```python\nfor item in items:\n    print(item)\n```'),
])
def test_reflow_preserves_structure_and_every_non_whitespace_character(source, expected):
    result, offsets = reflow(source)
    assert result == expected
    assert re.sub(r'\s', '', result) == re.sub(r'\s', '', source)
    assert len(result) == len(offsets) and offsets == sorted(offsets)
    assert all(char.isspace() or char == source[offsets[index]] for index, char in enumerate(result))
    assert reflow(result)[0] == result


def test_pdf_chunks_obey_limit_and_map_to_original_ranges():
    original = ('機關導入人工智慧服務之前，\n    應先評估隱私與安全風險並保留人工覆核。\n' * 20).rstrip()
    blocks = [{'id':'p1', 'page':7, 'kind':'paragraph', 'text':original}]
    untouched = deepcopy(blocks)
    values = documents.baseline(blocks, 100, reflow_pdf=True)
    chunks.validate(values, blocks)
    assert blocks == untouched
    assert all(len(chunk['content']) <= 100 and chunk['algorithm'] == 'pdf-reflow-v1' for chunk in values)
    assert re.sub(r'\s', '', ''.join(c['content'] for c in values)) == re.sub(r'\s', '', original)
    for value in values:
        for ref in value['refs']:
            assert ref['page'] == 7
            assert re.sub(r'\s', '', value['content']) == re.sub(r'\s', '', original[ref['start']:ref['end']])


def test_pdf_import_and_rechunk_reflow_without_changing_original(monkeypatch):
    original = '機關導入人工智慧時，\n應先評估隱私與安全風險並保留人工覆核。'
    page = Mock()
    page.extract_text.return_value = original
    monkeypatch.setattr(documents, 'PdfReader', lambda stream: Mock(pages=[page]))
    result = documents.create(b'original pdf bytes', 'guide.pdf', 'application/pdf', {'language':'zh-TW'})
    doc = documents.get(result['id'])
    assert store.get_bytes(doc.original_key) == b'original pdf bytes'
    assert doc.blocks[0]['text'] == original
    assert doc.draft[0]['content'] == original.replace('\n', '')
    saved = chunks.save(doc.id, doc.draft_revision, [], reset=True, chunk_size=100)
    assert saved['draft'][0]['content'] == doc.draft[0]['content']
    assert saved['blocks'] == doc.blocks and saved['original_hash'] == doc.original_hash
    assert saved['published_version'] == 0


def test_non_pdf_import_keeps_intentional_line_breaks():
    original = '機關導入人工智慧時，\n應先評估風險。'
    result = documents.create(original.encode(), 'guide.txt', 'text/plain', {'language':'zh-TW'})
    assert documents.get(result['id']).draft[0]['content'] == original


def test_reflow_preview_retains_unsaved_edits_and_does_not_persist(source):
    doc = documents.get(source['id'])
    unsaved = deepcopy(doc.draft)
    unsaved[0]['content'] = '人工修正內容，不改寫文字，\n僅整理排版換行。'
    result = chunks.preview_reflow(doc.id, doc.draft_revision, unsaved)
    assert result['changed'] == 1
    assert result['chunks'][0]['content'] == '人工修正內容，不改寫文字，僅整理排版換行。'
    assert result['chunks'][0]['refs'] == unsaved[0]['refs']
    assert documents.get(doc.id).draft == doc.draft
    assert documents.get(doc.id).draft_revision == doc.draft_revision
    saved = chunks.save(doc.id, doc.draft_revision, result['chunks'])
    assert saved['draft'] == result['chunks'] and saved['published_version'] == 0


def test_structured_table_blocks_are_never_reflowed(source):
    with store.session() as db:
        doc = db.get(store.Document, source['id'])
        doc.blocks = [{**block, 'kind':'table'} for block in doc.blocks]
        db.commit()
    doc = documents.get(source['id'])
    values = [{**chunk, 'content':'第一欄，\n第二欄，\n第三欄'} for chunk in doc.draft]
    assert chunks.preview_reflow(doc.id, doc.draft_revision, values) == {'chunks':values, 'changed':0}
