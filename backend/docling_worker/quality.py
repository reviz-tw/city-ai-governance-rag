"""Audit OCR confidence and layout coverage without rewriting source text."""
import unicodedata

OCR_POLICY = 'rapidocr-scan-fullpage-preserve-v1'


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text) if c.isalnum())


def audit_ocr(pages, page_text):
    """Compare retained OCR cells with assembled text, including headers/footers.

    A missing cell is a review signal, not permission to insert guessed text or
    duplicate a table. Samples stay in the document's private metadata; logs
    contain only page numbers and counts. Never claim detection of unseen text.
    """
    reports = []
    for page in pages:
        cells = [c for c in page.cells if getattr(c, 'from_ocr', False) and c.text.strip()]
        if not cells:
            continue
        assembled = normalized(page_text.get(page.page_no, ''))
        low = [c for c in cells if c.confidence < .5]
        missing = [c for c in cells if len(normalized(c.text)) >= 8 and normalized(c.text) not in assembled]
        def samples(values):
            return [dict(text=c.text[:500], confidence=round(float(c.confidence), 4)) for c in values[:10]]
        reports.append(dict(page=page.page_no, cells=len(cells), low_confidence=len(low),
                            unassembled=len(missing), low_confidence_samples=samples(low),
                            unassembled_samples=samples(missing)))
    warnings = []
    for field, code in [('low_confidence', 'OCR_LOW_CONFIDENCE'), ('unassembled', 'OCR_LAYOUT_COVERAGE')]:
        affected = [str(p['page']) for p in reports if p[field]]
        if affected:
            warnings.append(f'{code}: pages ' + ', '.join(affected))
    return reports, warnings
