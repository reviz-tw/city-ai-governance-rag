import {useEffect, useState} from 'react';
import {api} from '../lib/api';
type Account = {email:string; role:string; active:boolean};
const roles = {reader:'讀者', editor:'編輯者', admin:'管理員'};
export function AccountManagement({email, onClose}:{email:string; onClose:()=>void}) {
  const [accounts,setAccounts]=useState<Account[]>([]);
  const [newEmail,setNewEmail]=useState('');
  const [role,setRole]=useState('reader');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [ready,setReady]=useState(false);
  const load=async()=>{setAccounts(await api('/api/accounts'));setReady(true);};
  useEffect(()=>{load().catch(e=>setError(e.message));},[]);
  const save=async(path:string, method:string, body?:unknown)=>{
    setBusy(true);setError('');
    try {await api(path,{method,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});await load();if(method==='POST')setNewEmail('');}
    catch(e:any){setError(e.message);}finally{setBusy(false);}
  };
  return <section className="account-management" aria-label="帳號管理">
    <div className="account-heading"><h2>帳號管理</h2><button className="btn btn-secondary" onClick={onClose}>關閉</button></div>
    <p>讀者可查詢與使用研究工具；編輯者另可管理文件；管理員另可管理帳號與權限。新增後，使用者以該電子郵件的 Google 帳號登入。</p>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={e=>{e.preventDefault();save('/api/accounts','POST',{email:newEmail,role,active:true});}} className="account-create">
      <label>電子郵件<input className="input" type="email" required maxLength={320} value={newEmail} onChange={e=>setNewEmail(e.target.value)}/></label>
      <label>權限<select className="input" value={role} onChange={e=>setRole(e.target.value)}>{Object.entries(roles).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <button className="btn btn-primary" disabled={busy||!ready}>新增帳號</button>
    </form>
    {!ready && !error && <p role="status">載入中…</p>}
    <div className="account-list">{accounts.map(a=><article key={a.email} className="account-row">
      <strong>{a.email}</strong><span>{a.active?'啟用':'停用'}</span>
      <label>權限<select className="input" aria-label={`${a.email} 權限`} value={a.role} disabled={busy||a.email===email} onChange={e=>save(`/api/accounts/${encodeURIComponent(a.email)}`,'PATCH',{role:e.target.value,active:a.active})}>{Object.entries(roles).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <button className="btn btn-secondary" disabled={busy||a.email===email} onClick={()=>save(`/api/accounts/${encodeURIComponent(a.email)}`,'PATCH',{role:a.role,active:!a.active})}>{a.active?'停用':'啟用'}</button>
      <button className="btn btn-secondary" disabled={busy||a.email===email} onClick={()=>{if(window.confirm(`刪除 ${a.email} 的登入資格？既有文件將保留。`))save(`/api/accounts/${encodeURIComponent(a.email)}`,'DELETE');}}>刪除</button>
    </article>)}</div>
  </section>;
}
