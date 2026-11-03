import {useEffect, useState} from 'react';
import {api} from '../lib/api';
import {useLocale} from '../lib/locale';
type Account = {email:string; role:string; active:boolean};
const roles = ['reader', 'editor', 'admin'] as const;
export function AccountManagement({email, onClose}:{email:string; onClose:()=>void}) {
  const {t, error:errorText} = useLocale();
  const [accounts,setAccounts]=useState<Account[]>([]);
  const [newEmail,setNewEmail]=useState('');
  const [role,setRole]=useState('reader');
  const [error,setError]=useState<unknown>(null);
  const [busy,setBusy]=useState(false);
  const [ready,setReady]=useState(false);
  const load=async()=>{setAccounts(await api('/api/accounts'));setReady(true);};
  useEffect(()=>{load().catch(e=>setError(e));},[]);
  const save=async(path:string, method:string, body?:unknown)=>{
    setBusy(true);setError(null);
    try {await api(path,{method,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});await load();if(method==='POST')setNewEmail('');}
    catch(e:any){setError(e);}finally{setBusy(false);}
  };
  return <section className="account-management" aria-label={t('accounts')}>
    <div className="account-heading"><h2>{t('accounts')}</h2><button className="btn btn-secondary" onClick={onClose}>{t('close')}</button></div>
    <p>{t('accountIntro')}</p>
    {error != null && <p role="alert">{errorText(error)}</p>}
    <form onSubmit={e=>{e.preventDefault();save('/api/accounts','POST',{email:newEmail,role,active:true});}} className="account-create">
      <label>{t('email')}<input className="input" type="email" required maxLength={320} value={newEmail} onChange={e=>setNewEmail(e.target.value)}/></label>
      <label>{t('accountRole')}<select className="input" value={role} onChange={e=>setRole(e.target.value)}>{roles.map(value=><option key={value} value={value}>{t(`role_${value}`)}</option>)}</select></label>
      <button className="btn btn-primary" disabled={busy||!ready}>{t('addAccount')}</button>
    </form>
    {!ready && error == null && <p role="status">{t('loading')}</p>}
    <div className="account-list">{accounts.map(a=><article key={a.email} className="account-row">
      <strong>{a.email}</strong><span>{t(a.active?'accountActive':'accountInactive')}</span>
      <label>{t('accountRole')}<select className="input" aria-label={t('accountRoleLabel',{email:a.email})} value={a.role} disabled={busy||a.email===email} onChange={e=>save(`/api/accounts/${encodeURIComponent(a.email)}`,'PATCH',{role:e.target.value,active:a.active})}>{roles.map(value=><option key={value} value={value}>{t(`role_${value}`)}</option>)}</select></label>
      <button className="btn btn-secondary" disabled={busy||a.email===email} onClick={()=>save(`/api/accounts/${encodeURIComponent(a.email)}`,'PATCH',{role:a.role,active:!a.active})}>{t(a.active?'disableAccount':'enableAccount')}</button>
      <button className="btn btn-secondary" disabled={busy||a.email===email} onClick={()=>{if(window.confirm(t('deleteAccountPrompt',{email:a.email})))save(`/api/accounts/${encodeURIComponent(a.email)}`,'DELETE');}}>{t('delete')}</button>
    </article>)}</div>
  </section>;
}
