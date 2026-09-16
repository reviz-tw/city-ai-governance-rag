import {useEffect, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {CONTENT_LANGUAGES} from '../lib/languages';
import {ChatMessage} from '../types';

export function JobView({id, onClose}: {id: string; onClose: () => void}) {
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
      }).catch(e=>{if(!cancelled)setError(e.message);});
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
      } catch (err: any) { if (!stopped) setError(err.message); }
    };
    void refresh();
    return () => {stopped = true; clearTimeout(timer);};
  }, [id,refreshKey]);
  const act = async (action: string) => {
    try {setError(''); setJob(await api(`/api/artifacts/${id}/${action}`, jsonRequest({revision: job.revision, draft}))); setRefreshKey(v=>v+1);}
    catch (err: any) {setError(err.message);}
  };
  return <section className="workspace-panel" aria-label="產出任務">
    <div className="flex justify-between"><h2>{job?.kind==='index'?'切片發布':'產出預覽'}</h2><button onClick={onClose}>關閉</button></div>
    {error && <p role="alert">{error}</p>}
    {job && <><p>狀態：{job.status} · {job.progress}%</p>
      {job.kind==='index'&&['queued','running'].includes(job.status)&&<p>索引處理中，預計約 10～30 分鐘，實際依 Vertex 處理狀態而定。完成前維持前一發布版本；可關閉視窗，稍後從「我的產出」查看。</p>}
      {job.kind==='index'&&job.status==='completed'&&<p>已發布 v{job.result?.published_version}，{job.result?.verified_chunks} 個切片已通過搜尋驗證。</p>}
      {job.stale && <p role="alert">來源已更新，這份產出不是最新版本；請重新建立任務。</p>}
      {job.error && <p role="alert">{job.error}</p>}
      {draft && job.status === 'awaiting_review' && <>
        <p>請檢查內容、引用與限制；確認後才會渲染檔案。</p>
        {job.kind==='pptx'&&<p>目前大綱預計 {preview?.slide_count ?? '計算中…'} 頁（含限制與來源）；受眾：{job.audience}；語言：{job.language}。修改內容後會重新計算分頁。</p>}
        <label>標題<input value={draft.title} onChange={e => setDraft({...draft, title: e.target.value})}/></label>
        <label>摘要<textarea value={draft.summary} onChange={e => setDraft({...draft, summary: e.target.value})}/></label>
        {draft.sections.map((s: any, i: number) => <div key={i}>
          <input aria-label="段落標題" value={s.heading} onChange={e => setDraft({...draft, sections: draft.sections.map((v: any,j: number) => j === i ? {...v, heading:e.target.value}:v)})}/>
          <textarea aria-label="段落內容" value={s.body} onChange={e => setDraft({...draft, sections: draft.sections.map((v: any,j: number) => j === i ? {...v, body:e.target.value}:v)})}/>
          <small>{s.citations.map((c: any) => `${c.document_id}/${c.block_id}`).join(' · ')}</small>
        </div>)}
        <label>限制<textarea value={draft.limitations} onChange={e => setDraft({...draft, limitations: e.target.value})}/></label>
        {draft.chart && <div><h3>{draft.chart.title}</h3><p>{draft.chart.type}</p>{draft.chart.points?.map((p: any,i: number) => <p key={i}>{p.label}: {p.value} {p.unit} ({p.period}) — {p.quote}</p>)}{draft.chart.rows?.map((r: string[],i: number) => <p key={i}>{r.join(' | ')}</p>)}{draft.chart.labels?.map((s: string,i: number) => <p key={i}>{i+1}. {s}</p>)}</div>}
        <button className="btn btn-primary" disabled={job.kind==='pptx'&&!preview} onClick={() => act('confirm')}>確認內容並產出</button>
      </>}
      {job.kind === 'translation' && job.draft && <>
        <p>AI 輔助翻譯，非官方譯本。政策／法律判斷請回查原文。</p>
        {job.draft.complete&&<p>已完成選定擷取文字的翻譯；不包含原始圖片或原版面重製。</p>}
        {!job.draft.complete && <p>部分翻譯，尚未完成全文。</p>}
        {job.draft.source_versions?.map((s:any)=><p key={s.id}><a href={`/api/library/${s.id}/original`}>{s.title} · 原文</a><small> · {s.version.slice(0,12)}</small></p>)}
        {job.draft.blocks?.map((b: any) => <div className="parallel-text" key={b.id}><div dir="auto"><small>{b.id} · {b.page ?? '—'}</small><BlockText text={b.original} cells={b.original_cells}/></div><div dir="auto"><BlockText text={b.text} cells={b.cells}/>{b.ambiguity && <p>{b.ambiguity}</p>}</div></div>)}
      </>}
      {job.status === 'completed' && job.result?.files?.map((file: any) => <div key={file.name}>
        <a className="btn" href={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}`}>{file.name}</a>
        {file.mime === 'image/png' && <img alt="圖表預覽" src={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}`}/>}
        {file.mime === 'application/pdf' && <iframe title={file.name} src={`/api/artifacts/${id}/download/${encodeURIComponent(file.name)}?inline=true`} width="100%" height="520"/>}
      </div>)}
      {!['completed','failed','cancelled'].includes(job.status) && <button onClick={() => act('cancel')}>取消任務</button>}
      {['failed','cancelled'].includes(job.status) && <button onClick={() => act('retry')}>重試</button>}
      <button onClick={async () => {try {await api(`/api/artifacts/${id}`, {method:'DELETE'}); onClose();} catch (err: any) {setError(err.message);}}}>刪除任務與檔案</button>
    </>}
  </section>;
}

function BlockText({text,cells}:{text:string;cells?:string[][]}) {
  return cells ? <table><tbody>{cells.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell}</td>)}</tr>)}</tbody></table> : <p className="whitespace-pre-wrap">{text}</p>;
}

export function TaskHistory({onClose}:{onClose:()=>void}) {
  const [tasks,setTasks]=useState<any[]>([]);
  const [selected,setSelected]=useState('');
  const [error,setError]=useState('');
  useEffect(()=>{if(!selected) api('/api/artifacts').then(setTasks).catch(e=>setError(e.message));},[selected]);
  if(selected) return <JobView id={selected} key={selected} onClose={()=>setSelected('')}/>;
  return <section className="workspace-panel"><div className="flex justify-between"><h2>我的產出任務</h2><button onClick={onClose}>關閉</button></div>
    <p>重新開啟進行中的任務或下載尚未到期的產出。</p>{error&&<p role="alert">{error}</p>}
    {!tasks.length&&<p>目前沒有任務。</p>}{tasks.map(task=><div className="source-block" key={task.id}><button className="btn" onClick={()=>setSelected(task.id)}>{task.kind} · {task.status} · {task.progress}%</button><p>保存至 {new Date(task.expires_at*1000).toLocaleString()}</p></div>)}
  </section>;
}

export function ArtifactPanel({kind, messages, selectedMessage, onClose}: {kind: string; messages: ChatMessage[]; selectedMessage?: string; onClose: () => void}) {
  const [scope, setScope] = useState(selectedMessage ? 'answer' : 'conversation');
  const answers = messages.filter(m => m.role === 'assistant' && !m.isStreaming && !m.error && m.citations?.some(c => c.document_id));
  const [messageId, setMessageId] = useState(selectedMessage || answers.slice(-1)[0]?.id || '');
  const [language, setLanguage] = useState(answers.slice(-1)[0]?.response_language || 'zh-TW');
  const [audience, setAudience] = useState('研究與政策工作者');
  const [pages, setPages] = useState(6);
  const [job, setJob] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [sourceSelection,setSourceSelection]=useState<string[]|null>(null);
  useEffect(()=>setSourceSelection(null),[scope,messageId]);
  const selected = scope === 'answer' ? answers.filter(m => m.id === messageId) : answers.slice(-12);
  const candidates = [...new Set(selected.flatMap(m => m.citations?.map(c => c.document_id).filter(Boolean) || []))];
  const sources=(sourceSelection || candidates.slice(0,12)).filter(id=>candidates.includes(id));
  if (job) return <JobView id={job} onClose={onClose}/>;
  return <section className="workspace-panel">
    <div className="flex justify-between"><h2>{kind === 'chart' ? '製作圖表' : kind === 'pdf' ? '製作報告 PDF' : '產出投影片'}</h2><button onClick={onClose}>關閉</button></div>
    <label>內容範圍<select value={scope} onChange={e => setScope(e.target.value)}><option value="answer">這則回答</option><option value="conversation">這段對話（最近 12 則回答）</option></select></label>
    {scope === 'answer' && <select value={messageId} onChange={e => setMessageId(e.target.value)}>{answers.map(m => <option value={m.id} key={m.id}>{m.content.slice(0,80)}</option>)}</select>}
    <label>產出語言<select value={language} onChange={e => setLanguage(e.target.value)}>{Object.entries(CONTENT_LANGUAGES).map(([code,name]) => <option key={code} value={code}>{name}</option>)}</select></label>
    <label>受眾<input value={audience} onChange={e => setAudience(e.target.value)}/></label>
    {kind === 'pptx' && <label>目標頁數<input type="number" min={3} max={12} value={pages} onChange={e => setPages(Number(e.target.value))}/></label>}
    <details><summary>選擇原始來源（最多 12 份）</summary>{candidates.map(id=><label key={id}><input type="checkbox" checked={sources.includes(id)} disabled={!sources.includes(id)&&sources.length>=12} onChange={e=>setSourceSelection(e.target.checked?[...sources,id]:sources.filter(v=>v!==id))}/>{selected.flatMap(m=>m.citations||[]).find(c=>c.document_id===id)?.title || id}</label>)}</details>
    <p>選定 {selected.length} 則回答與 {sources.length} 份原始來源。先產生草稿供檢查，檔案保存 24 小時。</p>
    {error && <p role="alert">{error}</p>}
    <button className="btn btn-primary" disabled={busy || !sources.length} onClick={async () => {
      setBusy(true);
      try {const task = await api('/api/artifacts', jsonRequest({kind, scope, message_ids:selected.map(m=>m.id), source_ids:sources, context:selected.map(m=>m.content).join('\n').slice(0,6000), language, audience, pages})); setJob(task.id);}
      catch (err: any) {setError(err.message);} finally {setBusy(false);}
    }}>建立草稿</button>
  </section>;
}
