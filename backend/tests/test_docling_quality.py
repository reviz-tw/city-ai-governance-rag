from types import SimpleNamespace as N
from docling_worker.quality import audit_ocr


def cell(text, score=1., ocr=True):
    return N(text=text, confidence=score, from_ocr=ocr)


def test_low_confidence_line_is_auditable_even_when_assembled():
    text='本會已制定本府資料治理要點'
    report,warnings=audit_ocr([N(page_no=12,cells=[cell(text,.23)])],{12:text})
    assert report[0]['low_confidence']==1
    assert report[0]['unassembled']==0
    assert report[0]['low_confidence_samples']==[dict(text=text,confidence=.23)]
    assert warnings==['OCR_LOW_CONFIDENCE: pages 12']


def test_layout_omission_is_distinct_from_recognition_uncertainty():
    text='規範內部資料提供、申請、審核、維護'
    report,warnings=audit_ocr([N(page_no=12,cells=[cell(text,.97),cell('8')])],{12:'智慧行政業務'})
    assert report[0]['low_confidence']==0
    assert report[0]['unassembled']==1
    assert report[0]['unassembled_samples'][0]['text']==text
    assert warnings==['OCR_LAYOUT_COVERAGE: pages 12']


def test_spacing_punctuation_headers_and_native_cells_do_not_create_missing_text():
    report,warnings=audit_ocr([N(page_no=8,cells=[cell('１. 提升 資料品質'),cell('重要文件工作報告'),
        cell('not an OCR cell',.1,False)])],{8:'1.提升資料品質\n重要文件工作報告'})
    assert warnings==[]
    assert report[0]['cells']==2


def test_audit_is_page_specific_and_samples_are_bounded():
    cells=[cell('本頁辨識文字可能未被納入內容'+str(i),.1) for i in range(30)]
    report,warnings=audit_ocr([N(page_no=1,cells=cells)],{2:' '.join(c.text for c in cells)})
    assert report[0]['unassembled']==30
    assert len(report[0]['unassembled_samples'])==10
    assert len(report[0]['low_confidence_samples'])==10
    assert len(warnings)==2
