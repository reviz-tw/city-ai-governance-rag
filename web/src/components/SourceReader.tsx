import {WorkspacePanel} from './WorkspacePanel';
import {useEffect, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {CONTENT_LANGUAGES} from '../lib/languages';
import {useLocale} from '../lib/locale';
import {Citation, ChunkTranslationResult} from '../types';
import {sourceDisplayText} from '../lib/source-display';
import {TranslationPassages} from './TranslationPassages';

export function SourceReader({citation, language, onClose}: {citation:Citation; language:string; onClose:()=>void}) {
  const {t, error:errorText} = useLocale();
  const id = citation.document_id!;
  const [doc,setDoc] = useState<any>();
  const [target,setTarget] = useState(language);
  const [result,setResult] = useState<ChunkTranslationResult>();
  const [error,setError] = useState<unknown>();
  const [refresh,setRefresh] = useState(0);
  const selectionKey = JSON.stringify([id,citation.chunk_id,citation.block_ids,citation.version]);
  useEffect(()=>{
    let active=true;setDoc(undefined);setError(undefined);
    api(`/api/library/${encodeURIComponent(id)}`).then(value=>{if(active)setDoc(value);}).catch(e=>{if(active)setError(e);});
    return()=>{active=false;};
  },[id]);
  useEffect(()=>{
    let active=true;
    let timer:ReturnType<typeof setTimeout>;
    setResult(undefined);setError(undefined);
    if(!citation.chunk_id&&!citation.block_ids?.length)return;
    const body = {
      language:target,
      version:citation.chunk_id&&citation.version?Number(citation.version):undefined,
      original_hash:!citation.chunk_id?citation.version:undefined,
      chunk_ids:citation.chunk_id?[citation.chunk_id]:[],
      block_ids:citation.chunk_id?[]:citation.block_ids||[],
    };
    const query=new URLSearchParams({language:target});
    if(body.version!==undefined)query.set('version',String(body.version));
    if(body.original_hash)query.set('original_hash',body.original_hash);
    body.chunk_ids.forEach(value=>query.append('chunk_ids',value));
    body.block_ids.forEach(value=>query.append('block_ids',value));
    const path=`/api/library/${encodeURIComponent(id)}/translations`;
    const load=async(initial:boolean)=>{
      try {
        const value:ChunkTranslationResult=await api(initial?path:`${path}?${query}`,initial?jsonRequest(body):{});
        if(!active)return;
        setResult(value);setError(undefined);
        if(value.chunks.some(c=>['queued','running'].includes(c.status)))timer=setTimeout(()=>void load(false),5000);
      } catch(e) {if(active)setError(e);}
    };
    void load(true);
    return()=>{active=false;clearTimeout(timer);};
  },[selectionKey,target,refresh]);
  const blocks = (doc?.blocks || []).filter((b:any)=>citation.block_ids?.includes(b.id));
  return <WorkspacePanel title={t('readerTitle')} onClose={onClose}>
    {error&&<p role="alert">{errorText(error)}</p>}
    {!doc&&!error&&<p role="status">{t('loading')}</p>}
    {doc&&<>
      <h2>{doc.title}</h2>
      <p>{t('sourceLanguage')}: {CONTENT_LANGUAGES[doc.language as keyof typeof CONTENT_LANGUAGES]||doc.language} · {t('version')}: {result?.version??doc.published_version}</p>
      <a className="btn btn-secondary" href={`/api/library/${encodeURIComponent(id)}/original`} target="_blank" rel="noreferrer">{t('openOriginal')}</a>
      <label>{t('translateTarget')}<select value={target} onChange={e=>setTarget(e.target.value)}>{Object.entries(CONTENT_LANGUAGES).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label>
      <p>{t('translationNote')}</p>
      {result?<TranslationPassages result={result}/>:<>
        {!error&&(citation.chunk_id||citation.block_ids?.length)?<p role="status">{t('loading')}</p>:null}
        {blocks.length?blocks.map((b:any)=><section key={b.id} className="source-block" dir="auto"><small>{t('page')} {b.page??t('unknownPage')} · {b.id}</small><p className="source-passage">{sourceDisplayText(b.text)}</p></section>):<blockquote className="source-passage" dir="auto">{sourceDisplayText(citation.snippet||'')}</blockquote>}
      </>}
      <button className="btn btn-secondary" onClick={()=>setRefresh(v=>v+1)}>{t('refresh')}</button>
    </>}
  </WorkspacePanel>;
}
