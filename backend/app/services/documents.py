import hashlib
import html
import io
import re
import uuid
from pathlib import Path
from collections.abc import Mapping
from fastapi import HTTPException
from pypdf import PdfReader
from docx import Document as WordDocument
from sqlalchemy import and_, func, select
from app.services import store
from app.services.auth import User, require_user, require_editor
from app.services.languages import normalize_language, detect
from app.services.text_layout import reflow


def can_read(document: store.Document, user: User):
    return user.admin or document.owner == user.id or document.shared or user.email in document.readers


def get(document_id: str, user: User | None = None, *, edit=False):
    user = user or require_user()
    with store.session() as db:
        doc = db.get(store.Document, document_id)
        if doc is None or not can_read(doc, user):
            raise HTTPException(404, 'Document not found')
        if edit and (not user.editor or not (user.admin or doc.owner == user.id)):
            raise HTTPException(403, 'Document editing not permitted')
        return doc


def extract(data: bytes, filename: str):
    blocks, warnings = [], []
    def add(text, page=None, kind='paragraph', cells=None, **extra):
        if text.strip():
            blocks.append(dict(id=f'p{len(blocks)+1}', text=text.strip(), page=page,
                               kind=kind, cells=cells, **extra))
    ext = Path(filename).suffix.lower()
    if ext == '.pdf':
        reader = PdfReader(io.BytesIO(data))
        empty = []
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text(extraction_mode='layout') or ''
            if len(re.sub(r'\s', '', text)) < 30:
                empty.append(page_num)
            for paragraph in re.split(r'\n\s*\n', text):
                add(paragraph, page_num)
        if empty:
            warnings.append('OCR_REQUIRED: pages ' + ', '.join(map(str, empty)))
        warnings.append('PDF_LAYOUT_REVIEW: extracted text may not preserve complex tables or images')
    elif ext == '.docx':
        doc = WordDocument(io.BytesIO(data))
        from docx.oxml.ns import qn
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        table_number = 0
        for child in doc.element.body:
            if child.tag == qn('w:p'):
                paragraph = Paragraph(child, doc)
                add(paragraph.text, kind='heading' if paragraph.style.name.startswith('Heading') else 'paragraph')
            elif child.tag == qn('w:tbl'):
                table_number += 1
                for row_number, row in enumerate(Table(child, doc).rows, 1):
                    cells, seen = [], set()
                    for cell in row.cells:
                        if cell._tc not in seen:
                            seen.add(cell._tc)
                            cells.append(cell.text)
                    add('\t'.join(cells), kind='table', cells=[cells],
                        table_id=table_number, table_row=row_number)
    elif ext in {'.txt', '.md'}:
        for paragraph in re.split(r'\n\s*\n', data.decode('utf-8')):
            add(paragraph, kind='heading' if paragraph.startswith('#') else 'paragraph')
    else:
        raise HTTPException(415, 'Supported: PDF, DOCX, UTF-8 TXT and Markdown')
    if not blocks:
        raise HTTPException(422, 'No extractable text; OCR is required')
    if sum(len(b['text']) for b in blocks) > 500000:
        raise HTTPException(413, 'Document exceeds the text limit')
    return blocks, warnings


def baseline(blocks, limit=1500, *, reflow_pdf=False):
    chunks = []
    header = None
    header_ref = None

    def source_ref(block, start=0, end=None):
        return dict(block_id=block['id'], start=start,
                    end=len(block['text']) if end is None else end, page=block['page'])

    def add_table_row(block, value, refs, row_number=None, labels=None):
        # One row is the semantic unit. Long rows split between fields; every
        # fragment keeps its row/column context and source citation.
        prefix = f'第 {row_number} 列\n' if row_number else ''
        if labels is not None:
            fields = [(f'{labels[i].strip()}：' if i < len(labels) and labels[i].strip() else '', cell)
                      for i, cell in enumerate(value.split('\t')) if cell.strip()]
        else:
            fields = [('', line) for line in value.split('\n')]
        pieces = []
        for label, field in fields:
            field = field.strip()
            if not field:
                continue
            width = max(1, limit - len(prefix) - len(label))
            while len(field) > width:
                end = width
                boundary = max(field.rfind('\n', width // 2, end),
                               field.rfind('。', width // 2, end), field.rfind(' ', width // 2, end))
                if boundary > 0:
                    end = boundary + 1
                pieces.append(label + field[:end].strip())
                field = field[end:].strip()
            if field:
                pieces.append(label + field)
        current = prefix
        for piece in pieces:
            if len(current) + len(piece) + (1 if current and not current.endswith('\n') else 0) > limit and current.strip():
                chunks.append(dict(content=current.strip(), refs=refs, algorithm='table-row-v1'))
                current = prefix
            current += ('' if not current or current.endswith('\n') else '\n') + piece
        if current.strip():
            chunks.append(dict(content=current.strip(), refs=refs, algorithm='table-row-v1'))

    for block in blocks:
        text = block['text']
        if block.get('kind') == 'table':
            rows = block.get('cells') or []
            if rows:
                if len(rows) > 1:
                    header = rows[0]
                    header_ref = source_ref(block)
                    for index, row in enumerate(rows):
                        value = '\t'.join(row)
                        add_table_row(block, value, [source_ref(block)], index + 1,
                                      header if index else None)
                else:
                    row_number = block.get('table_row')
                    if row_number == 1:
                        header, header_ref = rows[0], source_ref(block)
                    refs = ([header_ref] if header and row_number != 1 and header_ref else []) + [source_ref(block)]
                    add_table_row(block, '\t'.join(rows[0]), refs, row_number,
                                  header if header and row_number != 1 else None)
            else:
                # Spreadsheet rows are already labelled with their sheet and
                # column names by the importer. Keep each row independent.
                header = header_ref = None
                add_table_row(block, text, [source_ref(block)])
            continue
        header = header_ref = None
        offsets = list(range(len(text)))
        if reflow_pdf and block.get('kind') not in {'table', 'heading', 'code'}:
            text, offsets = reflow(text)
        start = 0
        while start < len(text):
            end = min(start + limit, len(text))
            if end < len(text):
                boundary = max(text.rfind('\n', start + limit // 2, end),
                               text.rfind('。', start + limit // 2, end),
                               text.rfind('. ', start + limit // 2, end))
                if boundary > start:
                    end = boundary + 1
            value = text[start:end]
            if value.strip():
                chunks.append(dict(id=f'c{len(chunks)+1}', order=len(chunks), content=value,
                                   refs=[dict(block_id=block['id'], start=offsets[start], end=offsets[end-1]+1, page=block['page'])],
                                   algorithm='paragraph-v1'))
            start = end
    # Pack prose only. Tables must not absorb adjacent prose or other rows.
    packed=[]
    for chunk in chunks:
        if (packed and chunk['algorithm'] != 'table-row-v1' and
                packed[-1]['algorithm'] != 'table-row-v1' and
                len(packed[-1]['content'])+2+len(chunk['content'])<=limit):
            packed[-1]['content']+='\n\n'+chunk['content']
            packed[-1]['refs'].extend(chunk['refs'])
        else:
            packed.append(dict(chunk,id=f'c{len(packed)+1}',order=len(packed),
                               algorithm=chunk['algorithm'] if chunk['algorithm']=='table-row-v1' else 'paragraph-v2'))
    if reflow_pdf:
        for chunk in packed:
            if chunk['algorithm'] != 'table-row-v1':
                chunk['algorithm'] = 'pdf-reflow-v1'
    return packed


def create(data: bytes, filename: str, mime: str, metadata: dict, cleaned_text: str | None = None):
    user = require_editor()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, 'Upload limit: 20 MiB')
    from app.services import docling_pipeline
    parsed = docling_pipeline.parse(data, filename) if docling_pipeline.enabled() else None
    blocks, warnings = (parsed['blocks'], parsed['warnings']) if parsed else extract(data, filename)
    if parsed:
        metadata = {**metadata, 'docling': {k:parsed[k] for k in ('parser_version','tokenizer','max_tokens','schema_version')}}
    try:
        language = normalize_language(metadata.get('language') or detect('\n'.join(b['text'] for b in blocks)[:4000]) or 'zh-TW')
    except ValueError:
        raise HTTPException(422, 'Unsupported document language') from None
    document_id = uuid.uuid4().hex
    key = f'managed-originals/{document_id}/{hashlib.sha256(data).hexdigest()}/{Path(filename).name}'
    store.put_bytes(key, data, mime)
    draft = parsed['chunks'] if parsed else baseline(blocks, reflow_pdf=Path(filename).suffix.lower() == '.pdf')
    if cleaned_text is not None and cleaned_text.strip():
        # Human cleaned text is a draft; the extraction remains the immutable source.
        draft = baseline([dict(id='cleaned',text=cleaned_text,page=None)])
        for chunk in draft:
            chunk.update(refs=[dict(block_id=b['id'],start=0,end=len(b['text']),page=b['page']) for b in blocks],
                         algorithm='human-cleaned-paragraph-v1')
    with store.session() as db:
        doc = store.Document(id=document_id, owner=user.id, shared=False, readers=[], title=filename,
                             language=language, original_key=key, original_hash=hashlib.sha256(data).hexdigest(),
                             mime=mime, metadata_json=metadata, blocks=blocks, extraction_warnings=warnings,
                             draft=draft)
        db.add(doc)
        db.commit()
    return describe(doc)


def activity_for_documents(db, document_ids):
    """Summarize durable saves and submissions without loading revision contents."""
    if not document_ids:
        return {}
    activity = {document_id: {'last_draft_saved_at': None, 'last_index_submission': None,
                              'my_review': None}
                for document_id in document_ids}
    saved = db.execute(select(store.DraftRevision.document_id, func.max(store.DraftRevision.created_at))
                       .where(store.DraftRevision.document_id.in_(document_ids))
                       .group_by(store.DraftRevision.document_id))
    for document_id, created_at in saved:
        activity[document_id]['last_draft_saved_at'] = created_at
    latest = (select(store.Publication.document_id,
                     func.max(store.Publication.version).label('version'))
              .where(store.Publication.document_id.in_(document_ids))
              .group_by(store.Publication.document_id).subquery())
    submissions = db.execute(select(store.Publication.document_id, store.Publication.version,
                                    store.Publication.created_at, store.Publication.status)
                             .join(latest, and_(store.Publication.document_id == latest.c.document_id,
                                                store.Publication.version == latest.c.version)))
    for document_id, version, submitted_at, status in submissions:
        activity[document_id]['last_index_submission'] = dict(version=version, submitted_at=submitted_at,
                                                              status=status)
    current = {document_id: (version, status) for document_id, version, status in db.execute(
        select(store.Document.id, store.Document.published_version, store.Document.index_status)
        .where(store.Document.id.in_(document_ids)))}
    reviewer_id = require_user().id
    for review in db.scalars(select(store.DocumentReview).where(
            store.DocumentReview.document_id.in_(document_ids),
            store.DocumentReview.reviewer_id == reviewer_id)):
        version, status = current.get(review.document_id, (0, 'unpublished'))
        if version == review.version and status in {'indexed', 'indexed_cleanup_pending'}:
            activity[review.document_id]['my_review'] = dict(version=review.version,
                                                             reviewed_at=review.reviewed_at)
    return activity


def mark_reviewed(document_id: str, version: int, *, reviewed: bool = True):
    """Record only the signed-in editor's explicit acknowledgement of the live version."""
    user = require_editor()
    get(document_id, user, edit=True)
    with store.session() as db:
        doc = db.scalar(select(store.Document).where(store.Document.id == document_id).with_for_update())
        publication = db.get(store.Publication, f'{document_id}:{version}')
        if (doc.published_version != version or doc.index_status not in
                {'indexed', 'indexed_cleanup_pending'} or not publication or publication.status != 'published'):
            raise HTTPException(409, 'Published version changed; verify the current index before reviewing')
        key = f'{document_id}:{version}:{hashlib.sha256(user.id.encode()).hexdigest()[:32]}'
        existing = db.get(store.DocumentReview, key)
        if reviewed and existing is None:
            db.add(store.DocumentReview(id=key, document_id=document_id, version=version,
                                        reviewer_id=user.id, reviewer_email=user.email))
        elif not reviewed and existing is not None:
            db.delete(existing)
        db.commit()
        return describe(doc, include_content=True)


def describe(doc, include_content=False, activity=None):
    user = require_user()
    editable = user.editor and (user.admin or doc.owner == user.id)
    result = dict(id=doc.id, title=doc.title, language=doc.language, original_hash=doc.original_hash,
                  metadata=doc.metadata_json, warnings=doc.extraction_warnings,
                  draft_revision=doc.draft_revision, published_version=doc.published_version,
                  index_status=doc.index_status, shared=doc.shared, editable=editable,
                  has_structured_tables=any(b.get('kind') == 'table' for b in doc.blocks))
    if activity is None:
        with store.session() as db:
            activity = activity_for_documents(db, [doc.id])[doc.id]
    result.update(activity)
    if doc.id.startswith("legacy-"):
        from app.core.config import settings
        result["legacy_filename"] = doc.original_key.removeprefix(f"gs://{settings.GCS_BUCKET_NAME}/documents/")
    if editable:
        from app.core.config import settings
        from app.services import docling_pipeline
        result.update(docling_enabled=docling_pipeline.enabled())
        result.update(readers=doc.readers, indexing_enabled=settings.CHUNK_INDEX_ENABLED and bool(settings.CHUNK_DATA_STORE_ID))
    if include_content:
        result.update(blocks=doc.blocks)
        if editable:
            result['draft'] = doc.draft
    return result


def list_documents():
    user = require_user()
    with store.session() as db:
        visible = [d for d in db.scalars(select(store.Document)) if can_read(d, user)]
        activity = activity_for_documents(db, [d.id for d in visible])
        return [describe(d, activity=activity[d.id]) for d in visible]


def register_legacy(result):
    """Read-through catalogue of the pre-existing publicly served GCS collection."""
    require_user()
    link = result.get('link', '')
    from app.core.config import settings
    prefix = f'gs://{settings.GCS_BUCKET_NAME}/documents/'
    if not link.startswith(prefix):
        return None
    identifier = 'legacy-' + hashlib.sha256(link.encode()).hexdigest()[:32]
    with store.session() as db:
        if db.get(store.Document, identifier):
            return identifier
        filename = link.removeprefix(prefix)
        # Only this historical public collection is imported as shared.
        data = store.get_bytes(link)
        blocks, warnings = extract(data, filename)
        meta = result.get('metadata', {})
        db.add(store.Document(id=identifier, owner='legacy-public-collection', shared=True,
                             title=result['title'], language=normalize_language(meta.get('language') or detect('\n'.join(b['text'] for b in blocks)[:4000]) or 'zh-TW'),
                             original_key=link, original_hash=hashlib.sha256(data).hexdigest(),
                             mime='application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream',
                             metadata_json=meta, blocks=blocks, extraction_warnings=warnings,
                             draft=baseline(blocks, reflow_pdf=filename.lower().endswith('.pdf')), index_status='legacy-index', published_version=0))
        db.commit()
    return identifier


def evidence(document_id, user=None):
    doc = get(document_id, user)
    data = store.get_bytes(doc.original_key)
    current_hash = hashlib.sha256(data).hexdigest()
    if current_hash != doc.original_hash:
        raise HTTPException(409, 'Original file changed; re-import and review the new source version')
    # Re-read the authorized original representation, never the AI answer.
    return doc, [dict(**b, document_id=doc.id, version=doc.original_hash) for b in doc.blocks]


def plain_search_text(snippet):
    return html.unescape(re.sub(r'<[^>]+>', '', snippet))


def cited_passages(blocks, snippet):
    """Locate only substantial exact source text, never guess from a document title.

    Search snippets can contain markup, layout whitespace and ellipsis gaps.
    Matching returns complete original paragraph IDs for reading/translation.
    """
    plain = plain_search_text(snippet)
    fragments = [re.sub(r'\s+', '', part).casefold()
                 for part in re.split(r'\.{3,}|…+|[。!?！？\n]', plain)]
    fragments = [part for part in fragments if len(part) >= 16]
    # A snippet can bridge two PDF paragraphs without an ellipsis between them.
    # Require a substantial exact span inside each paragraph instead of requiring
    # the entire search excerpt to fit inside a single extraction block.
    spans = []
    for part in fragments:
        if len(part) <= 32:
            spans.append(part)
        else:
            spans.extend(part[start:start+32] for start in range(0, len(part)-31, 16))
            spans.append(part[-32:])
    found = []
    for block in blocks:
        text = re.sub(r'\s+', '', block['text']).casefold()
        if len(text) >= 16 and (any(part in text or text in part for part in fragments) or any(span in text for span in spans)):
            found.append(block['id'])
    return found
