import {useEffect,useState} from 'react';
import {api,jsonRequest} from '../lib/api';
import {useLocale} from '../lib/locale';
type Session={id:string;title:string;default_title?:boolean};
export function ConversationHistory({current,busy,revision,onSelect,onNew}:{current:string|null;busy:boolean;revision:number;onSelect:(id:string)=>void;onNew:()=>void}) {
  const {t,error:errorText} = useLocale();
  const [sessions,setSessions]=useState<Session[]>([]);
  const [error,setError]=useState<unknown>(null);
  const load=()=>api('/api/sessions').then(setSessions).catch(e=>setError(e));
  useEffect(()=>{load();},[current,revision]);
  const rename=async()=>{const title=window.prompt(t('conversationName'),sessions.find(s=>s.id===current)?.default_title?t('newConversation'):sessions.find(s=>s.id===current)?.title);if(!title?.trim())return;try{await api(`/api/sessions/${current}`,jsonRequest({title:title.trim()},'PATCH'));await load();}catch(e:any){setError(e);}};
  const remove=async()=>{if(!window.confirm(t('deleteConversationPrompt')))return;try{await api(`/api/sessions/${current}`,{method:'DELETE'});onNew();await load();}catch(e:any){setError(e);}};
  return <div className="conversation-history">
    <button className="btn btn-secondary" disabled={busy} onClick={onNew}>{t('newConversation')}</button>
    <label>{t('conversationHistory')} <select className="input" aria-label={t('conversationHistory')} value={current||''} disabled={busy} onChange={e=>e.target.value?onSelect(e.target.value):onNew()}><option value="">{t('newConversation')}</option>{sessions.map(s=><option key={s.id} value={s.id}>{s.default_title?t('newConversation'):s.title}</option>)}</select></label>
    {current && <><button className="btn" disabled={busy} onClick={rename}>{t('rename')}</button><button className="btn" disabled={busy} onClick={remove}>{t('delete')}</button></>}
    {error != null && <p role="alert">{errorText(error)}</p>}
  </div>;
}
