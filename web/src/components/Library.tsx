import {WorkspacePanel} from './WorkspacePanel';
import {ReactNode, useEffect, useRef, useState} from 'react';
import {api, apiList, ApiError, jsonRequest} from '../lib/api';
import {JobView} from './ArtifactPanel';
import {useLocale} from '../lib/locale';
import {ChunkDraftEditor} from './ChunkDraftEditor';
import {MAX_PUBLICATION_CHUNKS} from '../lib/chunks';

function LibraryFrame({standalone, editing, onClose, children}: {standalone:boolean; editing:boolean; onClose:()=>void; children:ReactNode}) {
  const {t} = useLocale();
  if (!standalone) return <WorkspacePanel title={t('library')} className={editing?'chunk-editor-panel':''} onClose={onClose}>{children}</WorkspacePanel>;
  return <main className={`admin-library ${editing?'is-editing':''}`}><header className="admin-library-header"><div>{!editing&&<p className="eyebrow">City AI governance · Admin</p>}<h1>{t('adminTitle')}</h1></div><nav><a href="/">{t('returnResearch')}</a><a href="/admin/tools/">{t('aiTools')}</a></nav></header>{children}</main>;
}

function DocumentActivity({document}: {document:any}) {
  const {t,date} = useLocale();
  const saved = document.last_draft_saved_at;
  const submission = document.last_index_submission;
  const status = submission?.status === 'published' ? t('indexed') :
    submission?.status === 'pending' ? t('pending') :
    submission?.status === 'failed' ? t('failed') :
    submission?.status === 'cancelled' ? t('cancelled') : t('error');
  return <div className="document-activity">
    <span>{saved ? t('lastDraftSaved',{date:date(saved)}) : t('neverSavedDraft')}</span>
    <span>{submission ? t('lastIndexSubmitted',{version:submission.version,date:date(submission.submitted_at),status}) : t('neverIndexSubmitted')}</span>
    {saved && submission && saved > submission.submitted_at && <span className="document-activity-unsent">{t('newerDraft')}</span>}
  </div>;
}

export function Library({editor, admin=false, standalone=false, onClose, onSessionExpired, onDraftDirtyChange}: {editor:boolean; admin?:boolean; standalone?:boolean; onClose:()=>void; onSessionExpired?:()=>void; onDraftDirtyChange?:(dirty:boolean)=>void}) {
  const {t, lang, error: errorText, label} = useLocale();
  const [confirmation, setConfirmation] = useState<'reset'|'leave'|null>(null);
  const editorHeading = useRef<HTMLHeadingElement>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [legacy, setLegacy] = useState<any[]>([]);
  const [legacyError, setLegacyError] = useState('');
  const [loading, setLoading] = useState(true);
  const [doc, setDoc] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState('');
  const [file, setFile] = useState<File|null>(null);
  const [rights, setRights] = useState(false);
  const [cleaned, setCleaned] = useState('');
  const [job, setJob] = useState('');
  const [diff, setDiff] = useState('');
  const [diffHash, setDiffHash] = useState('');
  const [savedDraft, setSavedDraft] = useState('');
  const [indexed, setIndexed] = useState<any>(null);
  const [language,setLanguage] = useState('');
  const [city,setCity] = useState('');
  const [chunkSize,setChunkSize] = useState(1500);
  const [reflowUndo,setReflowUndo] = useState<{before:any[];after:string}|null>(null);
  const [reflowMessage,setReflowMessage] = useState('');
  const loadDoc=(value:any)=>{setDoc(value);setSavedDraft(JSON.stringify(value.draft));setDiff('');setDiffHash('');setIndexed(null);setReflowUndo(null);setReflowMessage('');};
  useEffect(()=>{if(doc)editorHeading.current?.focus();},[doc?.id]);
  useEffect(()=>{
    if(!doc)return;
    const timer=window.setInterval(()=>{void api('/api/auth/me').catch(error=>{
      if(error instanceof ApiError && error.status===401)onSessionExpired?.();
    });},60000);
    return ()=>window.clearInterval(timer);
  },[doc?.id]);
  const dirty=doc && JSON.stringify(doc.draft)!==savedDraft;
  useEffect(()=>{onDraftDirtyChange?.(!!dirty);},[dirty,onDraftDirtyChange]);
  useEffect(()=>()=>onDraftDirtyChange?.(false),[onDraftDirtyChange]);
  useEffect(()=>{
    if(!dirty)return;
    const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);
    return ()=>window.removeEventListener('beforeunload',warn);
  },[dirty]);
  useEffect(()=>setDiffHash(''),[doc]);
  const refresh = async () => {
    setLoading(true);
    try {setDocs(await apiList('/api/library'));} catch(e:any) {setError(errorText(e));if(e instanceof ApiError && e.status===401)onSessionExpired?.();}
    finally {setLoading(false);}
  };
  const refreshLegacy = async () => {
    setLegacyError('');
    try {setLegacy(await apiList('/api/library/legacy'));} catch(e:any) {setLegacyError(errorText(e));if(e instanceof ApiError && e.status===401)onSessionExpired?.();}
  };
  useEffect(()=>{void refresh();void refreshLegacy();}, []);
  const run = async (action:()=>Promise<void>) => {
    setBusy(true);setError('');
    try {await action();} catch(e:any) {setError(errorText(e));if(e instanceof ApiError && e.status===401)onSessionExpired?.();} finally {setBusy(false);}
  };
  const save = async (reset=false) => {
    await run(async()=>{
      const result = await api(`/api/library/${doc.id}/draft`, jsonRequest({revision:doc.draft_revision, chunks:doc.draft, reset, chunk_size:reset ? chunkSize : undefined}));
      loadDoc(result);setDiff(t('saved'));await refresh();
    });
  };
  const openDocument = async (id:string) => {
    await run(async()=>loadDoc(await api(`/api/library/${id}`)));
  };
  const mutateChunks=(values:any[])=>setDoc({...doc,draft:values.map((value,order)=>({...value,order}))});
  const matches=(title:string)=>title.toLowerCase().includes(filter.toLowerCase());
  const historical=legacy.filter(item=>!docs.some(d=>d.legacy_filename===item.filename) && matches(item.filename));
  const pending=doc?.index_status==='pending';
  if(job) return <JobView id={job} onClose={()=>{setJob('');void refresh();if(doc)void run(async()=>loadDoc(await api(`/api/library/${doc.id}`)));}}/>;
  return <LibraryFrame standalone={standalone} editing={!!doc} onClose={onClose}>
    {!doc&&<p className="panel-intro">{t('libraryIntro')}</p>}
    {error && <p role="alert">{error}</p>}
    <fieldset disabled={busy} className="library-controls">
    {!doc && <>
    {editor && <details><summary>{t('newDocument')}</summary><label>{t('originalFile')}<input type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
      <label>{t('detectLanguage')}<input value={language} onChange={e=>setLanguage(e.target.value)} placeholder="zh-TW / en / ja"/></label>
      <label>{t('cityMetadata')}<input value={city} onChange={e=>setCity(e.target.value)}/></label>
      <label>{t('cleanedText')}<textarea value={cleaned} onChange={e=>setCleaned(e.target.value)}/></label>
      <label><input type="checkbox" checked={rights} onChange={e=>setRights(e.target.checked)}/>{t('rights')}</label>
      <button className="btn" disabled={!file||!rights} onClick={()=>run(async()=>{if(!file)return;const form=new FormData();form.append('file',file);form.append('rights_confirmed','true');form.append('language',language);form.append('city',city);if(cleaned)form.append('cleaned_text',cleaned);const d=await api('/api/library',{method:'POST',body:form});loadDoc(await api(`/api/library/${d.id}`));await refresh();})}>{t('uploadDraft')}</button>
    </details>}
    <div className="library-toolbar"><label>{t('searchDocuments')}<input value={filter} onChange={e=>setFilter(e.target.value)} placeholder={t('searchDocuments')}/></label><button className="btn" onClick={()=>run(async()=>{await refresh();await refreshLegacy();})}>{t('refresh')}</button></div>
    {loading && <p role="status">{t('loading')}</p>}
    {!loading && !docs.length && !legacy.length && !error && !legacyError && <p className="empty-panel">{t('noDocuments')}</p>}
    {docs.filter(d=>matches(d.title)).map(d=><div key={d.id} className="library-row"><div><strong>{d.title}</strong><p>{d.language} · {label(d.index_status)} · {t('publishedVersion',{version:d.published_version})} · {t('draftRevision',{revision:d.draft_revision})}</p><DocumentActivity document={d}/></div><div className="library-actions"><a className="btn btn-secondary" href={`/api/library/${d.id}/original`} target="_blank" rel="noreferrer">{t('openOriginal')}</a>{d.editable&&<button className="btn btn-ghost" onClick={()=>openDocument(d.id)}>{t('editChunks')}</button>}</div></div>)}
    {legacyError && <p role="alert">{legacyError}</p>}
    {historical.length>0 && <details><summary>{t('historical',{count:historical.length})}</summary><p>{t('historicalHint')}</p>{historical.map(item=><div className="library-row" key={item.filename}><div><strong>{item.filename}</strong><p>{item.language} · {t('legacy-index')}</p></div>{admin&&<button className="btn" onClick={()=>{
      void run(async()=>{loadDoc(await api('/api/library/legacy-draft',jsonRequest({filename:item.filename})));await refresh();});
    }}>{t('openDraft')}</button>}</div>)}</details>}
    </>}
    {doc?.editable && editor && <section className="chunk-editor" aria-label={t('editor')}><button className="btn btn-secondary" onClick={()=>dirty?setConfirmation('leave'):setDoc(null)}>{t('back')}</button><h2 tabIndex={-1} ref={editorHeading}>{doc.title} · {t('draftRevision',{revision:doc.draft_revision})}</h2><p>{label(doc.index_status)} · {t('publishedVersion',{version:doc.published_version})}</p><DocumentActivity document={doc}/>
      {doc.warnings?.length>0 && <p>{t('extractionNote')}</p>}
      <div className="chunk-reflow-tools"><button className="btn btn-secondary" onClick={()=>run(async()=>{
        const result=await api(`/api/library/${doc.id}/preview-reflow`,jsonRequest({revision:doc.draft_revision,chunks:doc.draft}));
        if(result.changed){setReflowUndo({before:doc.draft,after:JSON.stringify(result.chunks)});mutateChunks(result.chunks);}
        setReflowMessage(t(result.changed?'reflowDone':'reflowUnchanged',{count:result.changed}));
      })}>{t('reflowChunks')}</button>
        {reflowUndo&&JSON.stringify(doc.draft)===reflowUndo.after&&<button className="btn" onClick={()=>{mutateChunks(reflowUndo.before);setReflowUndo(null);setReflowMessage('');}}>{t('undoReflow')}</button>}
        <small>{t('reflowHint')}</small>
      </div>
      {reflowMessage&&<p role="status">{reflowMessage}</p>}
      <ChunkDraftEditor key={doc.id} chunks={doc.draft} blocks={doc.blocks||[]} onChange={mutateChunks}/>
      {doc.draft.length>MAX_PUBLICATION_CHUNKS&&<p role="status">{t('draftOverIndexLimit',{count:doc.draft.length,limit:MAX_PUBLICATION_CHUNKS.toLocaleString(lang)})}</p>}
      <div className="library-toolbar"><label>{t('chunkSize')}<input type="number" min="100" max="5000" value={chunkSize} onChange={e=>setChunkSize(Number(e.target.value))}/></label><button className="btn" disabled={!Number.isInteger(chunkSize)||chunkSize<100||chunkSize>5000} onClick={()=>setConfirmation('reset')}>{t('rechunk')}</button></div>
      <button className="btn" onClick={()=>save()}>{t('saveDraft')}</button>
      {dirty&&<p role="status">{t('unsaved')}</p>}
      <button className="btn" disabled={dirty} onClick={()=>run(async()=>{const d=await api(`/api/library/${doc.id}/diff?language=${lang}`);setDiff(d.diff||t('noChanges'));setDiffHash(d.hash);})}>{t('viewDiff')}</button>
      {diff&&<pre className="whitespace-pre-wrap publication-diff" aria-label={t('viewDiff')}>{diff}</pre>}
      <label><input type="checkbox" disabled={dirty} checked={doc.shared} onChange={e=>{const shared=e.target.checked;void run(async()=>loadDoc(await api(`/api/library/${doc.id}/sharing`,jsonRequest({shared,readers:doc.readers,revision:doc.draft_revision},'PATCH'))));}}/>{t('share')}</label>
      {!doc.indexing_enabled&&<p>{t('indexingDisabled')}</p>}
      {doc.indexing_enabled&&<p>{t('indexWaiting')}</p>}
      {pending&&<p role="status">{t('pendingHint')}</p>}
      <button className="btn btn-primary" disabled={!doc.indexing_enabled||dirty||!diffHash||pending||doc.draft.length>MAX_PUBLICATION_CHUNKS} onClick={()=>run(async()=>{const task=await api(`/api/library/${doc.id}/publish`,jsonRequest({revision:doc.draft_revision,reviewed_diff:diffHash}));setJob(task.id);})}>{t('publish')}</button>
      <button className="btn" disabled={!doc.indexing_enabled||doc.published_version<2||pending||dirty} onClick={()=>run(async()=>{const task=await api(`/api/library/${doc.id}/rollback`,jsonRequest({revision:doc.draft_revision}));setJob(task.id);})}>{t('rollback')}</button>
      <button className="btn" disabled={!doc.published_version} onClick={()=>run(async()=>setIndexed(await api(`/api/library/${doc.id}/indexed-chunks`)))}>{t('checkIndex')}</button>
      {indexed&&<div><h3>{t(indexed.verified?'verified':'notVerified',{version:indexed.version})}</h3>{indexed.chunks.map((c:any)=><p key={c.id} dir="auto">{c.id} · {c.content}</p>)}</div>}
    </section>}
    {confirmation && <div className="inline-confirmation" role="alert"><p>{t(confirmation==='reset'?'resetPrompt':'leavePrompt')}</p><button className="btn btn-primary" onClick={()=>{if(confirmation==='reset')void save(true);else setDoc(null);setConfirmation(null);}}>{t('confirm')}</button><button className="btn" onClick={()=>setConfirmation(null)}>{t('cancel')}</button></div>}
    </fieldset>
    {busy&&<p role="status">{t('busy')}</p>}
  </LibraryFrame>;
}
