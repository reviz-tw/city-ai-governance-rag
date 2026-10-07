import {useEffect,useState} from 'react';
import {api,jsonRequest} from '../lib/api';
type Session={id:string;title:string};
export function ConversationHistory({current,busy,revision,onSelect,onNew}:{current:string|null;busy:boolean;revision:number;onSelect:(id:string)=>void;onNew:()=>void}) {
  const [sessions,setSessions]=useState<Session[]>([]);
  const [error,setError]=useState('');
  const [summaries,setSummaries]=useState<any[]>([]);
  const [showSummary,setShowSummary]=useState(false);
  const load=()=>api('/api/sessions').then(setSessions).catch(e=>setError(e.message));
  useEffect(()=>{load();setShowSummary(false);},[current,revision]);
  const rename=async()=>{const title=window.prompt('對話名稱',sessions.find(s=>s.id===current)?.title);if(!title?.trim())return;try{await api(`/api/sessions/${current}`,jsonRequest({title:title.trim()},'PATCH'));await load();}catch(e:any){setError(e.message);}};
  const remove=async()=>{if(!window.confirm('刪除此對話、訊息及摘要紀錄？'))return;try{await api(`/api/sessions/${current}`,{method:'DELETE'});onNew();await load();}catch(e:any){setError(e.message);}};
  return <div className="conversation-history">
    <button className="btn btn-secondary" disabled={busy} onClick={onNew}>新增對話</button>
    <label>歷史對話 <select className="input" aria-label="歷史對話" value={current||''} disabled={busy} onChange={e=>e.target.value?onSelect(e.target.value):onNew()}><option value="">新對話</option>{sessions.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select></label>
    {current && <><button className="btn" disabled={busy} onClick={rename}>重新命名</button><button className="btn" disabled={busy} onClick={remove}>刪除</button><button className="btn" disabled={busy} onClick={async()=>{try{const value=await api(`/api/sessions/${current}`);setSummaries(value.summaries);setShowSummary(!showSummary);}catch(e:any){setError(e.message);}}}>摘要紀錄</button></>}
    {error && <p role="alert">{error}</p>}
    {showSummary && <div className="conversation-summaries"><p>摘要整合較早對話的研究脈絡，完整訊息仍保存。模型使用最新摘要與近期完整對話。</p>{!summaries.length?<p>尚未產生摘要；目前使用完整的近期對話。</p>:summaries.map((s,i)=><details key={s.id}><summary>摘要版本 {i+1} · 涵蓋至第 {s.through_sequence} 輪 · {new Date(s.created_at*1000).toLocaleString()}</summary><p>更新方式：{s.method.startsWith('model-v1')?'AI 摘要':'原文摘錄（摘要服務暫時無法使用）'}</p><pre>{s.text}</pre><div>摘要依據的原始對話：{s.source_turns?.map((turn:any)=><details key={turn.id}><summary>第 {turn.sequence} 輪：{turn.question.slice(0,80)}</summary><p>問題：{turn.question}</p><pre>回答：{turn.answer}</pre></details>)}</div></details>)}</div>}
  </div>;
}
