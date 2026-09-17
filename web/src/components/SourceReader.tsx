import {WorkspacePanel} from './WorkspacePanel';
import {useEffect, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {CONTENT_LANGUAGES} from '../lib/languages';
import {useLocale} from '../lib/locale';
import {Citation} from '../types';
import {JobView} from './ArtifactPanel';

export function SourceReader({citation, language, onClose}: {citation:Citation; language:string; onClose:()=>void}) {
  const {t, error:errorText} = useLocale();
  const id = citation.document_id!;
  const [doc,setDoc] = useState<any>();
  const [target,setTarget] = useState(language);
  const [ack,setAck] = useState(false);
  const [job,setJob] = useState('');
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  useEffect(()=>{let active=true;api(`/api/library/${id}`).then(value=>{if(active)setDoc(value);}).catch(e=>{if(active)setError(errorText(e));});return()=>{active=false;};},[id]);
  const blocks = (doc?.blocks || []).filter((b:any)=>citation.block_ids?.includes(b.id));
  const ocr = doc?.warnings?.some((w:string)=>{
    if(!w.startsWith('OCR_REQUIRED'))return false;
    const pages=w.match(/^OCR_REQUIRED: pages (\d+(?:,\s*\d+)*)$/)?.[1].split(',').map(Number);
    return !pages || blocks.some((b:any)=>b.page==null||pages.includes(b.page));
  });
  const stale = !!doc && !!citation.version && (citation.chunk_id ? String(doc.published_version)!==String(citation.version) : doc.original_hash!==citation.version);
  if(job)return <JobView id={job} onClose={()=>setJob('')}/>;
  return <WorkspacePanel title={t('readerTitle')} onClose={onClose}>
    {error&&<p role="alert">{error}</p>}
    {!doc&&!error&&<p role="status">{t('loading')}</p>}
    {doc&&<><h2>{doc.title}</h2><p>{t('sourceLanguage')}: {CONTENT_LANGUAGES[doc.language as keyof typeof CONTENT_LANGUAGES]||doc.language} · {t('version')}: {doc.original_hash.slice(0,12)}</p>
      <a className="btn btn-secondary" href={`/api/library/${id}/original`} target="_blank" rel="noreferrer">{t('openOriginal')}</a>
      {stale&&<p role="alert">{t('stale')}</p>}
      {!blocks.length?<><p>{t('noPassage')}</p><blockquote dir="auto">{citation.snippet}</blockquote></>:<>
        <p>{t('citedCount',{count:blocks.length})}</p>
        {blocks.map((b:any)=><section key={b.id} className="source-block" dir="auto"><small>{t('page')} {b.page??t('unknownPage')} · {b.id}</small><p className="whitespace-pre-wrap">{b.text}</p></section>)}
        <label>{t('translateTarget')}<select value={target} onChange={e=>setTarget(e.target.value)}>{Object.entries(CONTENT_LANGUAGES).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label>
        {doc.warnings?.length>0&&<><p>{t('extractionNote')}</p><label><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>{t('extractionAck')}</label></>}
        {blocks.length>50&&<p role="alert">{t('tooLarge')}</p>}
        {ocr&&<p role="alert">{t('ocrBlocked')}</p>}
        {target===doc.language&&<p>{t('sameLanguage')}</p>}
        <p>{t('translationNote')}</p>
        <button className="btn btn-primary" disabled={busy||ocr||stale||blocks.length>50||target===doc.language||(doc.warnings?.length>0&&!ack)} onClick={async()=>{
          setBusy(true);setError('');
          try {const task=await api('/api/artifacts',jsonRequest({kind:'translation',scope:'passage',source_ids:[id],block_ids:blocks.map((b:any)=>b.id),language:target,acknowledge_extraction_limits:ack}));setJob(task.id);}
          catch(e){setError(errorText(e));}finally{setBusy(false);}
        }}>{t(busy?'busy':'translatePassage')}</button>
      </>}
    </>}
  </WorkspacePanel>;
}
