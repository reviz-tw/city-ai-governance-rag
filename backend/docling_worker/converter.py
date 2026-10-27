"""Docling-only runtime. No database, cloud credentials or generation model."""
import hashlib
import json
import os
import time
import logging
from importlib.metadata import version
from pathlib import Path
from functools import lru_cache
try:
    from .quality import OCR_POLICY, audit_ocr
except ImportError:  # Converter is also launched directly in its isolated Python.
    from quality import OCR_POLICY, audit_ocr


@lru_cache(maxsize=1)
def document_converter(full_page_ocr=False):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions, OcrMode
    options=PdfPipelineOptions()
    options.do_ocr=True
    options.do_table_structure=True
    # RapidOCR otherwise silently drops entire recognized lines below 0.5.
    # Preserve uncertain text for human review instead of hiding it.
    options.ocr_options=RapidOcrOptions(text_score=0.0,
        mode=OcrMode.FULL_PAGE if full_page_ocr else OcrMode.DEFAULT)
    options.generate_parsed_pages=True
    if os.environ.get('DOCLING_ARTIFACTS_PATH'):
        options.artifacts_path=Path(os.environ['DOCLING_ARTIFACTS_PATH'])
    return DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options,backend=PyPdfiumDocumentBackend)})


def progress(stage,**fields):
    print(json.dumps({"event":"docling_progress","request_id":os.environ.get("DOCLING_REQUEST_ID"),"stage":stage,**fields}),flush=True)


def convert(path: Path, max_tokens=768):
    import tiktoken
    from docling.datamodel.base_models import ConversionStatus
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
    started=time.monotonic()
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    full_page_ocr=False
    progress('source_loaded',source_hash=digest,bytes=path.stat().st_size,pdf_backend='pypdfium2' if path.suffix.lower()=='.pdf' else None)
    if path.suffix.lower()=='.pdf':
        import pypdfium2 as pdfium
        pdf=pdfium.PdfDocument(path)
        try:
            native_text_pages=0
            for index in range(len(pdf)):
                page=pdf[index]
                try:
                    textpage=page.get_textpage()
                    try:text=textpage.get_text_range()
                    finally:textpage.close()
                    if sum(c.isalnum() for c in text)>=30:native_text_pages+=1
                finally:page.close()
            # Scans must not be cropped to imperfect layout detections before OCR.
            # Keep PDFium text extraction for PDFs with a usable native text layer.
            full_page_ocr=native_text_pages==0
            progress('pdf_loaded',pages=len(pdf),native_text_pages=native_text_pages,
                     ocr_mode='full_page' if full_page_ocr else 'pdf_aware_layout_regions')
        finally:pdf.close()
    progress('conversion_started')
    result=None
    if path.suffix.lower()=='.txt':
        from docling_core.types.doc import DoclingDocument, DocItemLabel
        document=DoclingDocument(name=path.stem)
        for paragraph in path.read_text(encoding='utf-8-sig').split('\n\n'):
            if paragraph.strip():document.add_text(label=DocItemLabel.PARAGRAPH,text=paragraph.strip())
    else:
        result=document_converter(full_page_ocr).convert(path)
        if result.status != ConversionStatus.SUCCESS:
            raise ValueError('Docling did not completely convert the document')
        document=result.document
    progress('conversion_completed',elapsed_seconds=round(time.monotonic()-started,2))
    progress('chunking_started')
    tokenizer=OpenAITokenizer(tokenizer=tiktoken.get_encoding('cl100k_base'),max_tokens=max_tokens)
    chunker=HybridChunker(tokenizer=tokenizer,merge_peers=True,repeat_table_header=True)
    blocks=[]; by_ref={}; page_text={}
    parser_version=version('docling')
    parser_identity=parser_version+(':pypdfium2' if path.suffix.lower()=='.pdf' else '')
    for item,_ in document.iterate_items():
        label=str(item.label.value)
        text=getattr(item,'text',None)
        if label=='table':text=item.export_to_markdown(doc=document)
        if not text or not text.strip():continue
        text=text.strip()
        for provenance in item.prov:
            page_text[provenance.page_no]=page_text.get(provenance.page_no,'')+'\n'+text
        if label in {'page_header','page_footer','picture'}: continue
        provenance=[p.model_dump(mode='json') for p in item.prov]
        pages=list(dict.fromkeys(p.page_no for p in item.prov)) or [None]
        kind='table' if label=='table' else 'heading' if label in {'section_header','title'} else 'code' if label=='code' else 'paragraph'
        refs=[]
        for page in pages:
            identifier='dl-'+hashlib.sha256(f'{digest}:{parser_identity}:{item.self_ref}:{page}:{text}'.encode()).hexdigest()[:32]
            block=dict(id=identifier,text=text,page=page,kind=kind,cells=None,
                docling_ref=item.self_ref,provenance=provenance,extraction='docling-'+parser_version)
            if kind=='table':block['table_data']=item.data.model_dump(mode='json')
            blocks.append(block)
            refs.append(dict(block_id=identifier,start=0,end=len(text),page=page))
        by_ref[item.self_ref]=refs
    values=[]
    for native in chunker.chunk(dl_doc=document):
        text=chunker.contextualize(native)
        refs=[]
        for item in native.meta.doc_items:
            refs.extend(by_ref.get(item.self_ref,[]))
        # Heading context is attached to embeddings and must remain attributable.
        headings=native.meta.headings or []
        source_positions=[i for i,b in enumerate(blocks) if any(r['block_id']==b['id'] for r in refs)]
        first=min(source_positions) if source_positions else len(blocks)
        for heading in headings:
            matching=[b for b in blocks[:first+1] if b['kind']=='heading' and b['text']==heading]
            if matching:
                block=matching[-1]
                refs.append(dict(block_id=block['id'],start=0,end=len(block['text']),page=block['page']))
        refs=list({(r['block_id'],r['start'],r['end']):r for r in refs}.values())
        if not refs:raise ValueError('Docling chunk has no original document element')
        if not text.strip() or len(text)>12000:raise ValueError('Docling chunk exceeds application limits')
        values.append(dict(id='dlc'+str(len(values)+1),order=len(values),content=text,refs=refs,
            algorithm='docling-hybrid-v1',headings=headings,token_count=tokenizer.count_tokens(text)))
    if not values or not blocks:raise ValueError('Docling returned no source text')
    if sum(len(b['text']) for b in blocks)>1000000:raise ValueError('Document exceeds extraction limit')
    audit,warnings=audit_ocr(result.pages,page_text) if result is not None else ([],[])
    for page in audit:
        progress('ocr_quality',**{k:page[k] for k in ('page','cells','low_confidence','unassembled')})
    progress('chunking_completed',chunks=len(values),blocks=len(blocks),elapsed_seconds=round(time.monotonic()-started,2))
    return dict(blocks=blocks,chunks=values,warnings=warnings,ocr_policy=OCR_POLICY,ocr_audit=audit,original_hash=digest,
        parser_version=parser_version,pdf_backend='pypdfium2' if path.suffix.lower()=='.pdf' else None,tokenizer='cl100k_base',max_tokens=max_tokens,
        source_reference_precision='document-element',schema_version=1)


if __name__=='__main__':
    import sys
    logging.basicConfig(level=logging.INFO,format=os.environ.get('DOCLING_REQUEST_ID','local')+' %(name)s %(levelname)s %(message)s')
    if sys.argv[1]=='--serve':
        from contextlib import redirect_stdout
        for line in sys.stdin:
            try:
                request=json.loads(line)
                with redirect_stdout(sys.stderr):
                    result=convert(Path(request['input']),int(request['max_tokens']))
                Path(request['output']).write_text(json.dumps(result,ensure_ascii=False))
                response={'ok':True}
            except Exception as exc:
                print(str(exc),file=sys.stderr,flush=True)
                response={'ok':False}
            print(json.dumps(response),flush=True)
    else:
        result=convert(Path(sys.argv[1]),int(sys.argv[3]))
        Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False))
