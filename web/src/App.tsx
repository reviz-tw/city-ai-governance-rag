import {useEffect, useState} from 'react';
import {Header} from './components/Header';
import {ChatView} from './components/ChatView';
import {Login} from './components/Login';
import {ArtifactPanel,TaskHistory} from './components/ArtifactPanel';
import {SourceReader} from './components/SourceReader';
import {Library} from './components/Library';
import {MCPAccess} from './components/MCPAccess';
import {ChatMessage} from './types';
import {STRINGS} from './i18n';
import {normalizeInterfaceLanguage, CONTENT_LANGUAGES} from './lib/languages';
import {api} from './lib/api';
import {readSSE} from './lib/sse';
import {workspaceLabels} from './lib/workspace-labels';

export default function App() {
  const [lang, setLang] = useState(() => normalizeInterfaceLanguage(new URLSearchParams(location.search).get('lang') || localStorage.getItem('interface_language')));
  const [user, setUser] = useState<any>(null);
  const [checking, setChecking] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [contextBoundary, setContextBoundary] = useState(0);
  const [summary, setSummary] = useState('');
  const [contextCity, setContextCity] = useState<string|null>(null);
  const [city, setCity] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [panel, setPanel] = useState(new URLSearchParams(location.search).has('admin') ? 'library' : '');
  const [sourceId, setSourceId] = useState('');
  const t = STRINGS[lang];
  const labels=workspaceLabels(lang);
  useEffect(() => {api('/api/auth/me').then(setUser).catch(() => {}).finally(() => setChecking(false));}, []);
  useEffect(() => {localStorage.setItem('interface_language', lang); document.documentElement.lang = lang === 'zh' ? 'zh-TW' : lang; document.documentElement.dir = 'ltr';}, [lang]);
  const clear = () => {setMessages([]); setContextBoundary(0); setSummary(''); setContextCity(null); setCity(''); setSources([]);};
  const send = async (text: string) => {
    if (loading) return;
    const now = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    const id = crypto.randomUUID();
    const history = messages.slice(contextBoundary).slice(-6).map(m => ({id:m.id, role:m.role, content:m.content.slice(0,12000), source_ids:m.citations?.map(c=>c.document_id).filter(Boolean) || [], response_language:m.response_language}));
    setMessages(prev => [...prev, {id:crypto.randomUUID(), role:'user', content:text, timestamp:now}, {id, role:'assistant', content:'', timestamp:now, isStreaming:true}]);
    setLoading(true);
    const update = (changes: Partial<ChatMessage>) => setMessages(prev => prev.map(m => m.id === id ? {...m,...changes} : m));
    let content = '';
    try {
      const response = await fetch('/api/chat/stream', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:text, city:city || null, response_language:'auto', interface_language:lang === 'zh' ? 'zh-TW':lang, source_languages:sources, research_context:{history, summary, city:contextCity}})});
      if (!response.ok || !response.body) throw new Error(`Request failed (${response.status})`);
      for await (const event of readSSE(response.body)) {
        if (event.type === 'sources') {
          update({citations:event.sources, response_language:event.response_language});
          setSummary(event.context_summary || ''); setContextCity(event.context_city || null);
        } else if (event.type === 'chunk') {content += event.text; update({content});}
        else if (event.type === 'error') {update({error:event.message}); if (!content) update({content:event.message});}
      }
    } catch (e: any) {update({content:content || e.message, error:e.message});}
    finally {update({isStreaming:false}); setLoading(false);}
  };
  if (checking) return <p className="p-8">Loading…</p>;
  if (!user) return <Login onLogin={setUser}/>;
  return <div className="flex flex-col h-screen min-h-[640px] bg-[var(--color-bg)] text-[var(--color-text)] font-body overflow-hidden">
    <Header t={t} lang={lang} onLangChange={setLang}/>
    <div className="research-toolbar">
      <label>{labels.city}<input value={city} disabled={loading} onChange={e => {setCity(e.target.value); setContextCity(null); setSummary(''); setContextBoundary(messages.length);}} placeholder={labels.allCities}/></label>
      <label>{labels.sources}<select multiple value={sources} onChange={e => setSources(Array.from(e.target.selectedOptions, o=>o.value))}>{Object.entries(CONTENT_LANGUAGES).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label>
      <button className="btn" onClick={() => setSources([])}>{labels.allSources}</button>
      <button className="btn" disabled={!messages.some(m=>!m.isStreaming&&!m.error&&m.citations?.some(c=>c.document_id))} onClick={()=>setPanel('chart')}>{labels.chart}</button>
      <button className="btn" disabled={!messages.some(m=>!m.isStreaming&&!m.error&&m.citations?.some(c=>c.document_id))} onClick={()=>setPanel('pdf')}>{labels.report}</button>
      <button className="btn" disabled={!messages.some(m=>!m.isStreaming&&!m.error&&m.citations?.some(c=>c.document_id))} onClick={()=>setPanel('pptx')}>{labels.slides}</button>
      <button className="btn" onClick={()=>setPanel('library')}>{labels.library}</button>
      <button className="btn" onClick={()=>setPanel('tasks')}>{labels.tasks}</button>
      <button className="btn" onClick={()=>setPanel('mcp')}>MCP</button>
      <small title={user.email}>{user.email}</small>
      <button className="btn" onClick={async()=>{await api('/api/auth/logout',{method:'POST'}); clear();setUser(null);}}>{labels.logout}</button>
    </div>
    <div className="flex-1 flex min-h-0 relative">
      <ChatView t={t} messages={messages} loading={loading} onSendMessage={send} onClearHistory={clear} onOpenSource={setSourceId}/>
      {['chart','pdf','pptx'].includes(panel) && <ArtifactPanel kind={panel} messages={messages} onClose={()=>setPanel('')} key={panel}/>}
      {panel === 'library' && <Library editor={user.editor} onClose={()=>setPanel('')} onRead={setSourceId}/>}
      {panel === 'tasks' && <TaskHistory onClose={()=>setPanel('')}/>}
      {panel === 'mcp' && <MCPAccess onClose={()=>setPanel('')}/>}
      {sourceId && <SourceReader id={sourceId} language={[...messages].reverse().find(m=>m.response_language)?.response_language || 'zh-TW'} onClose={()=>setSourceId('')} key={sourceId}/>}
    </div>
  </div>;
}
