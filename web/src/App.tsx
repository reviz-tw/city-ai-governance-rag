import {useCallback, useEffect, useState} from 'react';
import {ConversationHistory} from './components/ConversationHistory';
import {AccountManagement} from './components/AccountManagement';
import {Header} from './components/Header';
import {ChatView} from './components/ChatView';
import {Login} from './components/Login';
import {ArtifactPanel,TaskHistory} from './components/ArtifactPanel';
import {SourceReader} from './components/SourceReader';
import {Library} from './components/Library';
import {MCPAccess} from './components/MCPAccess';
import {ChatMessage, Citation} from './types';
import {STRINGS} from './i18n';
import {normalizeInterfaceLanguage} from './lib/languages';
import {api, ApiError} from './lib/api';
import {readSSE} from './lib/sse';
import {LocaleProvider} from './lib/locale';
import {panelText, panelError} from './lib/panel-copy';

export default function App() {
  const adminMode = /^\/admin\/?$/.test(location.pathname) || new URLSearchParams(location.search).has('admin');
  const [lang, setLang] = useState(() => normalizeInterfaceLanguage(new URLSearchParams(location.search).get('lang') || localStorage.getItem('interface_language')));
  const [user, setUser] = useState<any>(null);
  const [checking, setChecking] = useState(true);
  const [sessionId,setSessionId]=useState<string|null>(null);
  const [sessionsReady,setSessionsReady]=useState(false);
  const [sessionRevision,setSessionRevision]=useState(0);
  const [restoring,setRestoring]=useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [panel, setPanel] = useState('');
  const [source, setSource] = useState<{citation:Citation;language:string}|null>(null);
  const [artifact, setArtifact] = useState<{kind:string;message:ChatMessage}|null>(null);
  const t = STRINGS[lang];
  const [authError, setAuthError] = useState('');
  const [reauthenticating, setReauthenticating] = useState(false);
  const [hasUnsavedDraft, setHasUnsavedDraft] = useState(false);
  const handleReauth = useCallback((next:any) => {
    if(next.email.toLowerCase()!==user?.email.toLowerCase()) {setAuthError(panelText(lang,'reauthSameAccount'));return;}
    setUser(next);setAuthError('');setReauthenticating(false);
  },[user?.email,lang]);
  useEffect(() => {api('/api/auth/me').then(setUser).catch(() => {}).finally(() => setChecking(false));}, []);
  useEffect(() => {localStorage.setItem('interface_language', lang); document.documentElement.lang = lang === 'zh' ? 'zh-TW' : lang; document.documentElement.dir = 'ltr';}, [lang]);
  useEffect(()=>{
    if(!user)return;
    let active=true;
    setSessionsReady(false);
    api('/api/sessions').then(async sessions=>{
      if(!active)return;
      const saved=localStorage.getItem(`conversation:${user.email}`);
      const selected=sessions.find((s:any)=>s.id===saved)||sessions[0];
      if(selected){const value=await api(`/api/sessions/${selected.id}`);if(active){setSessionId(selected.id);setMessages(value.messages);}}
    }).catch(e=>{if(active)setAuthError(e.message);}).finally(()=>{if(active)setSessionsReady(true);});
    return ()=>{active=false;};
  },[user?.email]);
  useEffect(()=>{if(user&&sessionsReady){if(sessionId)localStorage.setItem(`conversation:${user.email}`,sessionId);else localStorage.removeItem(`conversation:${user.email}`);}},[user?.email,sessionId,sessionsReady]);
  const restore=async(id:string)=>{
    setRestoring(true);setAuthError('');
    try{const value=await api(`/api/sessions/${id}`);setSessionId(id);setMessages(value.messages);setSource(null);setArtifact(null);}
    catch(e:any){setAuthError(e.message);}finally{setRestoring(false);}
  };
  const clear = () => {setSessionId(null);setSource(null);setArtifact(null);setMessages([]);};
  const send = async (text: string) => {
    if (loading||restoring||!sessionsReady) return;
    const now = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    const id = crypto.randomUUID();

    setMessages(prev => [...prev, {id:crypto.randomUUID(), role:'user', content:text, timestamp:now}, {id, role:'assistant', content:'', timestamp:now, isStreaming:true}]);
    setLoading(true);
    const update = (changes: Partial<ChatMessage>) => setMessages(prev => prev.map(m => m.id === id ? {...m,...changes} : m));
    let content = '';
    try {
      let activeSession=sessionId;
      if(!activeSession){const created=await api('/api/sessions',{method:'POST'});activeSession=created.id;setSessionId(activeSession);}
      const response = await fetch('/api/chat/stream', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:activeSession,query:text, city:null, response_language:'auto', interface_language:lang === 'zh' ? 'zh-TW':lang, source_languages:[]})});
      if (!response.ok || !response.body) throw new ApiError(`Request failed (${response.status})`,response.status);
      for await (const event of readSSE(response.body)) {
        if (event.type === 'sources') {
          update({citations:event.sources, response_language:event.response_language});
        } else if (event.type === 'chunk') {content += event.text; update({content});}
        else if (event.type === 'error') {update({error:event.message}); if (!content) update({content:event.message});}
      }
    } catch (e: any) {const message=panelText(lang,panelError(e)); update({content:content || message, error:message});}
    finally {update({isStreaming:false}); setLoading(false);setSessionRevision(v=>v+1);}
  };
  if (checking) return <div className="app-loading" role="status"><span className="brand-dot"/>{panelText(lang,'loading')}</div>;
  if (!user) return <Login onLogin={setUser}/>;
  return <LocaleProvider lang={lang}><div className="app-shell">
    <Header admin={user.admin} t={t} lang={lang} onLangChange={setLang} email={user.email} loading={loading} onPanel={setPanel}
      onLogout={async () => {
        if (hasUnsavedDraft) {setAuthError(panelText(lang,'saveBeforeLogout'));return;}
        try {await api('/api/auth/logout', {method:'POST'}); clear(); setPanel(''); setSource(null); setArtifact(null); setUser(null);}
        catch (error: any) {setAuthError(panelText(lang,panelError(error)));}
      }}/>
    {authError && <p className="app-alert" role="alert">{authError}</p>}
    {!adminMode && <ConversationHistory current={sessionId} busy={loading||restoring||!sessionsReady} revision={sessionRevision} onSelect={restore} onNew={clear}/>}
    <div className="research-workspace">
      {!adminMode && <ChatView t={t} lang={lang} messages={messages} loading={loading||restoring||!sessionsReady} onSendMessage={send} onClearHistory={clear} onOpenSource={(citation,language)=>setSource({citation,language})} onArtifact={(kind,message)=>setArtifact({kind,message})}/>}
      {artifact && <ArtifactPanel kind={artifact.kind} message={artifact.message} onClose={()=>setArtifact(null)} key={`${artifact.kind}-${artifact.message.id}`}/>}
      {adminMode && <Library admin={user.admin} standalone editor={user.editor} onSessionExpired={()=>setReauthenticating(true)} onDraftDirtyChange={setHasUnsavedDraft} onClose={()=>location.assign('/')}/>}
      {panel === 'accounts' && user.admin && <AccountManagement email={user.email} onClose={()=>setPanel('')}/>}
      {panel === 'tasks' && <TaskHistory onClose={()=>setPanel('')}/>}
      {panel === 'mcp' && <MCPAccess onClose={()=>setPanel('')}/>}
      {source && <SourceReader citation={source.citation} language={source.language} onClose={()=>setSource(null)} key={`${source.citation.document_id}-${source.citation.citation_id}`}/>}
    </div>
    {reauthenticating && <div className="session-reauth-overlay" role="dialog" aria-modal="true" aria-label={panelText(lang,'expired')}>
      <p role="status">{panelText(lang,'reauthDraft')}</p>
      {authError && <p role="alert">{authError}</p>}
      <Login onLogin={handleReauth}/>
    </div>}
  </div></LocaleProvider>;
}
