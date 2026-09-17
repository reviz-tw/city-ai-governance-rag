import {WorkspacePanel} from './WorkspacePanel';
import {useEffect, useState} from 'react';
import {api, apiList, jsonRequest} from '../lib/api';
import {CONTENT_LANGUAGES} from '../lib/languages';
import {useLocale} from '../lib/locale';
import {answerEvidence} from '../lib/answer-artifact';
import {ChatMessage} from '../types';
import {GoogleSlidesExport} from './GoogleSlidesExport';
import {SlideDraftEditor} from './SlideDraftEditor';

export function JobView({id, onClose}: {id: string; onClose: () => void}) {
  const {t, error: errorText, label} = useLocale();
  const [job, setJob] = useState<any>(null);
  const [draft, setDraft] = useState<any>(null);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [preview,setPreview]=useState<any>(null);
  useEffect(()=>{
    setPreview(null);
    if (!draft || job?.status!=='awaiting_review' || job.kind!=='pptx') return;
    let cancelled=false;
    const timer=setTimeout(()=>{
      api(`/api/artifacts/${id}/preview-draft`,jsonRequest({revision:job.revision,draft})).then(value=>{
        if(!cancelled) {setPreview(value);setError('');}
      }).catch(e=>{if(!cancelled)setError(errorText(e));});
    },400);
    return ()=>{cancelled=true;clearTimeout(timer);};
  },[draft,job?.revision,job?.status,id]);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await api(`/api/artifacts/${id}`);
        if (!stopped) {
          setJob(value);
          if (value.status === 'awaiting_review') setDraft((previous: any) => previous || value.draft);
          if (['queued','running','render_queued'].includes(value.status)) timer = setTimeout(refresh,2500);
        }
      } catch (err: any) { if (!stopped) setError(errorText(err)); }
    };
    void refresh();
    return () => {stopped = true; clearTimeout(timer);};
  }, [id,refreshKey]);
  const act = async (action: string) => {
    try {setError(''); setJob(await api(`/api/artifacts/${id}/${action}`, jsonRequest({revision: job.revision, draft}))); setRefreshKey(v=>v+1);}
    catch (err: any) {setError(errorText(err));}
  };
  return <WorkspacePanel title={t(job?.kind==='index'?'index':'preview')} onClose={onClose}>
    {error && <p role="alert">{error}</p>}
    {job && <><p className="job-status">{label(job.status)} · {job.progress}%</p><progress className="job-progress" value={job.progress} max={100} aria-label={t('progress')}/>
      {job.kind==='index'&&['queued','running'].includes(job.status)&&<p>{t('indexWaiting')}</p>}
      {job.kind==='index'&&job.status==='completed'&&<p>{t('indexDone',{version:job.result?.published_version,count:job.result?.verified_chunks})}</p>}
      {job.stale && <p role="alert">{t('stale')}</p>}
      {job.error && <div role="alert"><p>{t('error')}</p><details><summary>{t('details')}</summary><p>{job.error}</p></details></div>}
      {draft && job.status === 'awaiting_review' && <>
        <p>{t('reviewDraft')}</p>
        {job.kind==='pptx'&&<p>{t(draft.slides?.length?'slideDeckPlan':'slidePlan',{count:preview?.slide_count ?? t('loading')})}</p>}
        <label>{t('title')}<input value={draft.title} onChange={e => setDraft({...draft, title: e.target.value})}/></label>
        <label>{t('summary')}<textarea value={draft.summary} onChange={e => setDraft({...draft, summary: e.target.value})}/></label>
        {!!draft.slides?.length && <SlideDraftEditor draft={draft} onChange={setDraft}/>}
        {!draft.slides?.length && draft.sections.map((s: any, i: number) => <div key={i}>
          <input aria-label={t('sectionTitle')} value={s.heading} onChange={e => setDraft({...draft, sections: draft.sections.map((v: any,j: number) => j === i ? {...v, heading:e.target.value}:v)})}/>
          <textarea aria-label={t('sectionBody')} value={s.body} onChange={e => setDraft({...draft, sections: draft.sections.map((v: any,j: number) => j === i ? {...v, body:e.target.value}:v)})}/>
          <small>{s.citations.map((c: any) => `${c.document_id}/${c.block_id}`).join(' · ')}</small>
        </div>)}
        <label>{t('limitations')}<textarea value={draft.limitations} onChange={e => setDraft({...draft, limitations: e.target.value})}/></label>
        {draft.chart && <div><h3>{draft.chart.title}</h3>{draft.chart.points?.map((p: any,i: number) => <p key={i}>{p.label}: {p.value} {p.unit} ({p.period}) — {p.quote}</p>)}{draft.chart.rows?.map((r: string[],i: number) => <p key={i}>{r.join(' | ')}</p>)}{draft.chart.labels?.map((s: string,i: number) => <p key={i}>{i+1}. {s}</p>)}</div>}
        <button className="btn btn-primary" disabled={job.kind==='pptx'&&!preview} onClick={() => act('confirm')}>{t('confirmOutput')}</button>
      </>}
      {job.kind === 'translation' && job.draft && <>
        <p>{t('translationNote')}</p>
        {job.draft.complete&&<p>{t('translationComplete')}</p>}
        {!job.draft.complete && <p>{t('translationPartial')}</p>}
        {job.draft.source_versions?.map((s:any)=><p key={s.id}><a href={`/api/library/${s.id}/original`}>{s.title} · {t('original')}</a><small> · {s.version.slice(0,12)}</small></p>)}
        {job.draft.blocks?.map((b: any) => <div className="parallel-text" key={b.id}><div dir="auto"><small>{b.id} · {b.page ?? '—'}</small><BlockText text={b.original} cells={b.original_cells}/></div><div dir="auto"><BlockText text={b.text} cells={b.cells}/>{b.ambiguity && <p>{b.ambiguity}</p>}</div></div>)}
      </>}
      {job.status === 'completed' && job.kind === 'pptx' && job.result?.files && <GoogleSlidesExport key={`${job.id}:${job.revision}`} job={job}/>}
      {job.status === 'completed' && job.result?.files?.map((file: any) => <div key={file.name}>
        <a className="btn" href={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}`}>{file.name}</a>
        {file.mime === 'image/png' && <img alt={t('chartPreview')} src={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}`}/>}
        {file.mime === 'application/pdf' && <iframe title={file.name} src={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}?inline=true`} width="100%" height="520"/>}
      </div>)}
      {!['completed','failed','cancelled'].includes(job.status) && <button onClick={() => act('cancel')}>{t('cancelTask')}</button>}
      {['failed','cancelled'].includes(job.status) && <button onClick={() => act('retry')}>{t('retry')}</button>}
      <button onClick={async () => {try {await api(`/api/artifacts/${id}`, {method:'DELETE'}); onClose();} catch (err: any) {setError(errorText(err));}}}>{t('deleteTask')}</button>
    </>}
  </WorkspacePanel>;
}

function BlockText({text,cells}:{text:string;cells?:string[][]}) {
  return cells ? <table><tbody>{cells.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell}</td>)}</tr>)}</tbody></table> : <p className="whitespace-pre-wrap">{text}</p>;
}

export function TaskHistory({onClose}:{onClose:()=>void}) {
  const {t, error: errorText, label, date} = useLocale();
  const [tasks,setTasks]=useState<any[]>([]);
  const [loading,setLoading]=useState(true);
  const [selected,setSelected]=useState('');
  const [error,setError]=useState('');
  useEffect(()=>{if(!selected) {setLoading(true); apiList('/api/artifacts').then(setTasks).catch(e=>setError(errorText(e))).finally(()=>setLoading(false));}},[selected]);
  if(selected) return <JobView id={selected} key={selected} onClose={()=>setSelected('')}/>;
  return <WorkspacePanel title={t('tasks')} onClose={onClose}>
    <p className="panel-intro">{t('tasksIntro')}</p>{error&&<p role="alert">{error}</p>}
    {loading && <p role="status">{t('loading')}</p>}
    {!loading && !tasks.length && !error && <p className="empty-panel">{t('noTasks')}</p>}
    <div className="task-list">{tasks.map(task=><button className={`task-card status-${task.status}`} key={task.id} onClick={()=>setSelected(task.id)}>
      <span className="task-card-title"><span className="task-dot"/>{label(task.kind)} · {label(task.status)}<span>{task.progress}%</span></span>
      <span className="task-expiry">{t('expires',{date:date(task.expires_at)})}</span>
      {['queued','running','render_queued'].includes(task.status) && <progress className="job-progress" value={task.progress} max={100} aria-label={t('progress')}/>}
    </button>)}</div>
  </WorkspacePanel>;
}

export function ArtifactPanel({kind, message, onClose}: {kind:string; message:ChatMessage; onClose:()=>void}) {
  const {t, error:errorText} = useLocale();
  const [language,setLanguage] = useState(message.response_language || 'zh-TW');
  const [audience,setAudience] = useState('');
  const [pages,setPages] = useState(6);
  const [job,setJob] = useState('');
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const evidence = answerEvidence(message);
  if(job) return <JobView id={job} onClose={onClose}/>;
  return <WorkspacePanel title={t(kind==='pdf'?'createPdf':kind==='pptx'?'createSlides':'createChart')} onClose={onClose}>
    <p className="panel-intro">{t('artifactIntro')}</p>
    <blockquote className="answer-excerpt" dir="auto">{message.content.slice(0,400)}</blockquote>
    <p>{t('answerSources',{count:evidence.source_ids.length})}</p>
    <div className="artifact-fields">
      <label>{t('targetLanguage')}<select value={language} onChange={e=>setLanguage(e.target.value)}>{Object.entries(CONTENT_LANGUAGES).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label>
      <label>{t('audience')}<input value={audience} placeholder={t('defaultAudience')} onChange={e=>setAudience(e.target.value)}/></label>
      {kind==='pptx'&&<label>{t('pages')}<input type="number" min={3} max={12} value={pages} onChange={e=>setPages(Number(e.target.value))}/></label>}
    </div>
    {evidence.source_ids.length>12&&<p role="alert">{t('tooLarge')}</p>}
    {!evidence.source_ids.length&&<p>{t('noSources')}</p>}
    {error&&<p role="alert">{error}</p>}
    <button className="btn btn-primary" disabled={busy||!evidence.source_ids.length||evidence.source_ids.length>12||!Number.isInteger(pages)||pages<3||pages>12} onClick={async()=>{
      setBusy(true);setError('');
      try {const task=await api('/api/artifacts',jsonRequest({kind,...evidence,language,audience:audience||t('defaultAudience'),pages}));setJob(task.id);}
      catch(e){setError(errorText(e));}finally{setBusy(false);}
    }}>{t(busy?'busy':'createDraft')}</button>
  </WorkspacePanel>;
}
