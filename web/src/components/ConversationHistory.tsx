import {useEffect,useState} from 'react';
import {api,jsonRequest} from '../lib/api';
type Session={id:string;title:string};
export function ConversationHistory({current,busy,revision,onSelect,onNew}:{current:string|null;busy:boolean;revision:number;onSelect:(id:string)=>void;onNew:()=>void}) {
  const [sessions,setSessions]=useState<Session[]>([]);
  const [error,setError]=useState('');
  const load=()=>api('/api/sessions').then(setSessions).catch(e=>setError(e.message));
  useEffect(()=>{load();},[current,revision]);
  const rename=async()=>{const title=window.prompt('對話名稱',sessions.find(s=>s.id===current)?.title);if(!title?.trim())return;try{await api(`/api/sessions/${current}`,jsonRequest({title:title.trim()},'PATCH'));await load();}catch(e:any){setError(e.message);}};
  const remove=async()=>{if(!window.confirm('刪除此對話及所有訊息？'))return;try{await api(`/api/sessions/${current}`,{method:'DELETE'});onNew();await load();}catch(e:any){setError(e.message);}};
  return <div className="conversation-history">
    <button className="btn btn-secondary" disabled={busy} onClick={onNew}>新增對話</button>
    <label>歷史對話 <select className="input" aria-label="歷史對話" value={current||''} disabled={busy} onChange={e=>e.target.value?onSelect(e.target.value):onNew()}><option value="">新對話</option>{sessions.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select></label>
    {current && <><button className="btn" disabled={busy} onClick={rename}>重新命名</button><button className="btn" disabled={busy} onClick={remove}>刪除</button></>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
