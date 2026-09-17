import {useState, useRef, useEffect, FormEvent, KeyboardEvent} from 'react';
import {BookOpen, Check, Copy, RotateCcw} from 'lucide-react';
import {ChatMessage, Citation} from '../types';
import {UIStrings} from '../i18n';
import {CONTENT_LANGUAGES, InterfaceLanguage} from '../lib/languages';
import {researchCopy} from '../lib/research-copy';
import {useLocale} from '../lib/locale';
import {WorkspacePanel} from './WorkspacePanel';

interface ChatViewProps {
  t: UIStrings; lang: InterfaceLanguage; messages: ChatMessage[]; loading: boolean;
  onSendMessage: (text: string) => void; onClearHistory: () => void; onOpenSource: (citation:Citation, language:string) => void; onArtifact: (kind:string,message:ChatMessage)=>void;
}

export function ChatView({t, lang, messages, loading, onSendMessage, onClearHistory, onOpenSource, onArtifact}: ChatViewProps) {
  const {t: text} = useLocale();
  const c = researchCopy(lang);
  const [inputText, setInputText] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [copiedId, setCopiedId] = useState('');
  const [copyError, setCopyError] = useState('');
  const [sourceMessageId, setSourceMessageId] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<number | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const scrollArea = useRef<HTMLDivElement>(null);
  const followStream = useRef(true);
  const input = useRef<HTMLTextAreaElement>(null);
  const copyTimer = useRef<ReturnType<typeof setTimeout>>();
  const latestAnswer = [...messages].reverse().find(m => m.role === 'assistant');
  const sourceMessage = messages.find(m => m.id === sourceMessageId) || latestAnswer;
  const citations = sourceMessage?.citations || [];

  useEffect(() => {
    setSourceMessageId(latestAnswer?.id || ''); setSelectedCitation(null); setCopyError('');
    followStream.current = true;
  }, [latestAnswer?.id]);
  useEffect(() => {
    if (followStream.current && scrollArea.current) scrollArea.current.scrollTop = scrollArea.current.scrollHeight;
  }, [messages, loading]);
  useEffect(() => {
    if (input.current) {input.current.style.height = 'auto'; input.current.style.height = `${Math.min(input.current.scrollHeight, 140)}px`;}
  }, [inputText]);
  useEffect(() => () => clearTimeout(copyTimer.current), []);

  const handleSubmit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!inputText.trim() || loading || isComposing) return;
    followStream.current = true;
    onSendMessage(inputText.trim()); setInputText('');
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !isComposing && !event.nativeEvent.isComposing && event.keyCode !== 229) {
      event.preventDefault(); handleSubmit();
    }
  };
  const showSources = (message: ChatMessage, citation?: Citation) => {
    setSourceMessageId(message.id); setSelectedCitation(citation?.citation_id ?? null);
    if (window.matchMedia('(max-width: 1100px)').matches) setSourcesOpen(true);
    else if (citation) requestAnimationFrame(() => document.getElementById(`source-${message.id}-${citation.citation_id}`)?.scrollIntoView({block:'nearest', behavior:'smooth'}));
  };
  const copy = async (message: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(message.content); setCopiedId(message.id); setCopyError('');
      clearTimeout(copyTimer.current); copyTimer.current = setTimeout(() => setCopiedId(''), 2000);
    } catch {setCopyError(c.copyError);}
  };
  const inline = (text: string, message: ChatMessage) => text.split(/(\*\*.*?\*\*|\[\d+\])/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2,-2)}</strong>;
    const match = part.match(/^\[(\d+)\]$/);
    const citation = match && message.citations?.find(item => item.citation_id === Number(match[1]));
    if (citation) return <button key={index} className="citation-chip" aria-label={`${t.sourceCitationBadge} ${citation.citation_id}: ${citation.title}`} aria-pressed={sourceMessage?.id === message.id && selectedCitation === citation.citation_id} onClick={() => showSources(message, citation)}>{citation.citation_id}</button>;
    return part;
  });
  const formatted = (message: ChatMessage) => message.content.split('\n').map((line, index) => {
    if (!line.trim()) return <div className="paragraph-break" key={index}/>;
    const heading = line.match(/^(#{1,3})\s+(.+)/);
    if (heading) return <h3 className={`answer-heading heading-${heading[1].length}`} key={index}>{inline(heading[2], message)}</h3>;
    const bullet = line.match(/^([-*]|\d+\.)\s+(.+)/);
    if (bullet) return <div className="answer-list-item" key={index}><span>{/\d/.test(bullet[1]) ? bullet[1] : '•'}</span><div>{inline(bullet[2], message)}</div></div>;
    return <p key={index}>{inline(line, message)}</p>;
  });

  const sourceCards = <>
    {!citations.length ? <p className="sources-empty">{c.sourceEmpty}</p> : <div className="source-cards">
      {citations.map(citation => <article key={citation.citation_id} id={`source-${sourceMessage?.id}-${citation.citation_id}`} className={`citation-card ${selectedCitation === citation.citation_id ? 'is-selected' : ''}`}>
        <button className="citation-card-select" aria-expanded={selectedCitation === citation.citation_id} onClick={() => setSelectedCitation(selectedCitation === citation.citation_id ? null : citation.citation_id)}>
          <span className="citation-card-title"><span className="citation-number">[{citation.citation_id}]</span><strong>{citation.title}</strong></span>
          <span className="citation-meta">{CONTENT_LANGUAGES[citation.language as keyof typeof CONTENT_LANGUAGES] || citation.language}{citation.page_start != null && ` · ${c.page} ${citation.page_start}${citation.page_end && citation.page_end !== citation.page_start ? `–${citation.page_end}` : ''}`}</span>
          {citation.snippet && <span className="citation-snippet" dir="auto">{citation.snippet}</span>}
        </button>
        {selectedCitation === citation.citation_id && <div className="citation-actions">
          {citation.document_id ? <button className="btn btn-secondary" onClick={() => {setSourcesOpen(false); onOpenSource(citation,sourceMessage?.response_language || (lang==='zh'?'zh-TW':lang));}}>{c.read}</button> : citation.link && /^https?:\/\//i.test(citation.link) ? <a className="btn btn-secondary" href={citation.link} target="_blank" rel="noreferrer">{c.read}</a> : null}
        </div>}
      </article>)}
      <p className="field-hint">{c.sourceHint}</p>
    </div>}
  </>;

  return <>
    <main className="chat-view">
      <div className="compact-source-bar"><button className="btn btn-ghost" onClick={() => setSourcesOpen(true)}><BookOpen size={15}/>{c.sourceToggle}{citations.length > 0 && <span className="count-badge">{citations.length}</span>}</button></div>
      <div className="chat-scroll" ref={scrollArea} onScroll={event => {const el = event.currentTarget; followStream.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100;}}>
        {messages.length === 0 ? <div className="welcome">
          <span className="welcome-dot"/>
          <h1>{t.welcomeTitle}</h1><p className="welcome-description">{t.welcomeDesc}</p>
          <h2 className="eyebrow">{c.samples}</h2>
          <div className="sample-questions">{t.sampleQuestions.map(question => <button key={question} disabled={loading} onClick={() => onSendMessage(question)}>{question}</button>)}</div>
          <div className="welcome-steps">{c.steps.map((step, index) => <div key={step}><span>0{index + 1}</span><p>{step}</p></div>)}</div>
        </div> : <div className="conversation">
          {messages.map(message => message.role === 'user' ? <div className="user-message" key={message.id}><p dir="auto">{message.content}</p></div> : <article className="assistant-message" key={message.id}>
            {message.isStreaming && !message.content && <div className="search-status" role="status"><span className="loading-dots"><i/><i/><i/></span><span>{t.searchingText}</span></div>}
            <div className="answer-content" dir="auto" lang={message.response_language}>{formatted(message)}</div>
            {message.error && <p role="alert" className="error-message">{message.error}</p>}
            {message.isStreaming && message.content && <span className="streaming-mark" role="status" aria-label={t.searchingText}/>}
            {!message.isStreaming && <footer className="answer-footer">
              <span className="answer-time">{message.timestamp}</span>
              {!!message.citations?.length && <button className="btn btn-ghost answer-sources" onClick={() => showSources(message)}><BookOpen size={14}/>{t.sourcesHeader} · {message.citations.length}</button>}
              <button className="btn btn-ghost" disabled={!message.content} onClick={() => void copy(message)}>{copiedId === message.id ? <Check size={13}/> : <Copy size={13}/>}{copiedId === message.id ? t.copiedBtn : t.copyBtn}</button>
              {!message.error && message.citations?.some(c=>c.document_id) && <>{(['pdf','pptx','chart'] as const).map(kind=><button className="btn btn-ghost" key={kind} onClick={()=>onArtifact(kind,message)}>{text(kind==='pdf'?'createPdf':kind==='pptx'?'createSlides':'createChart')}</button>)}</>}
              <button className="btn btn-ghost" disabled={loading} onClick={onClearHistory} title={t.clearHistoryTitle}><RotateCcw size={13}/>{t.restartBtn}</button>
            </footer>}
          </article>)}
          {copyError && <p role="alert" className="error-message">{copyError}</p>}
        </div>}
      </div>
      <div className="composer">
        <form onSubmit={handleSubmit}>
          <textarea ref={input} rows={1} dir="auto" value={inputText} onChange={e => setInputText(e.target.value)} onKeyDown={handleKeyDown} onCompositionStart={() => setIsComposing(true)} onCompositionEnd={() => setIsComposing(false)} placeholder={t.inputPlaceholder} aria-label={t.inputPlaceholder} readOnly={loading}/>
          <button className="btn btn-primary send-button" disabled={!inputText.trim() || loading || isComposing} aria-label={t.sendAriaLabel}>{c.send}</button>
        </form>
        <p>{t.multilingualNote}</p>
      </div>
    </main>
    <aside className="sources-sidebar" aria-label={c.sourceTitle}><div className="sources-header"><h2 className="eyebrow">{c.sourceTitle}</h2></div>{sourceCards}</aside>
    {sourcesOpen && <WorkspacePanel title={c.sourceTitle} className="sources-panel" onClose={() => setSourcesOpen(false)}>{sourceCards}</WorkspacePanel>}
  </>;
}
