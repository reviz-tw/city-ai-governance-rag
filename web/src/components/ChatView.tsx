import { useState, useRef, useEffect, FC, FormEvent, KeyboardEvent } from 'react';
import { Topic, ChatMessage, Citation } from '../types';
import { UIStrings } from '../i18n';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
  RotateCcw,
  BookOpen,
  HelpCircle,
  X
} from 'lucide-react';

interface ChatViewProps {
  t: UIStrings;
  topic: Topic;
  messages: ChatMessage[];
  loading: boolean;
  onSendMessage: (text: string) => void;
  onClearHistory: () => void;
  onOpenTopics: () => void;
}

export const ChatView: FC<ChatViewProps> = ({
  t,
  topic,
  messages,
  loading,
  onSendMessage,
  onClearHistory,
  onOpenTopics,
}) => {
  const [inputText, setInputText] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new message / streaming update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || loading || isComposing) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      if (isComposing || (e.nativeEvent && (e.nativeEvent as any).isComposing)) {
        return;
      }
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Render markdown-like formatted content
  const renderFormattedContent = (content: string, citations?: Citation[]) => {
    const lines = content.split('\n');
    return (
      <div className="space-y-2 text-[14px] leading-relaxed text-[var(--color-text)] font-body">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-1.5" />;

          // Headers
          if (line.startsWith('### ')) {
            return (
              <h4 key={idx} className="font-heading text-base text-[var(--color-text)] mt-3 mb-1 font-bold">
                {line.replace('### ', '')}
              </h4>
            );
          }
          if (line.startsWith('## ')) {
            return (
              <h3 key={idx} className="font-heading text-lg text-[var(--color-text)] mt-3.5 mb-1 font-bold">
                {line.replace('## ', '')}
              </h3>
            );
          }
          if (line.startsWith('# ')) {
            return (
              <h2 key={idx} className="font-heading text-xl text-[var(--color-text)] mt-4 mb-2 font-bold">
                {line.replace('# ', '')}
              </h2>
            );
          }

          // Bullet lists
          if (line.startsWith('* ') || line.startsWith('- ')) {
            const clean = line.substring(2);
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="text-[var(--color-accent)] font-bold mt-0.5">•</span>
                <div className="flex-1">{parseInlineFormatting(clean, citations)}</div>
              </div>
            );
          }

          // Numbered lists
          const numMatch = line.match(/^(\d+)\.\s(.*)/);
          if (numMatch) {
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="font-bold text-[var(--color-accent-700)] text-xs mt-0.5">
                  {numMatch[1]}.
                </span>
                <div className="flex-1">{parseInlineFormatting(numMatch[2], citations)}</div>
              </div>
            );
          }

          return <p key={idx} className="m-0">{parseInlineFormatting(line, citations)}</p>;
        })}
      </div>
    );
  };

  // Inline parse for bold **text** and citations [1]
  const parseInlineFormatting = (text: string, citations?: Citation[]) => {
    const parts = text.split(/(\*\*.*?\*\*|\[\d+\])/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-[var(--color-text)]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      const citeMatch = part.match(/^\[(\d+)\]$/);
      if (citeMatch && citations) {
        const citeId = parseInt(citeMatch[1], 10);
        const citeObj = citations.find((c) => c.citation_id === citeId);
        return (
          <button
            key={i}
            type="button"
            onClick={() => citeObj && setSelectedCitation(citeObj)}
            className="inline-flex items-center mx-0.5 px-1.5 py-0.2 rounded-full text-[11px] font-bold bg-[var(--color-accent-100)] text-[var(--color-accent-800)] hover:bg-[var(--color-accent-200)] border border-[var(--color-accent-400)] transition-colors cursor-pointer"
            title={citeObj ? `查看文獻來源: ${citeObj.title}` : `來源 [${citeId}]`}
          >
            [{citeId}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
      {/* Top Focus Bar */}
      <div className="flex-none flex items-center gap-3 px-5 py-3 border-b border-[var(--color-neutral-200)] bg-[var(--color-bg)] z-10">
        <Sparkles className="icn text-[var(--color-accent-600)]" />
        <span className="text-xs sm:text-[13px] text-[var(--color-neutral-600)] flex-none">
          {t.focusLabel}
        </span>
        <span className="text-xs sm:text-[13.5px] font-bold text-[var(--color-text)] truncate">
          {topic.title}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={onClearHistory}
              className="btn btn-ghost text-xs px-2.5 py-1 text-[var(--color-neutral-600)] hover:text-red-700"
              title="清除當前對話紀錄"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.restartBtn}</span>
            </button>
          )}
          <button
            type="button"
            onClick={onOpenTopics}
            className="btn btn-secondary text-xs px-3.5 py-1.5 font-heading"
          >
            {t.switchBtn}
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl w-full mx-auto flex flex-col items-center gap-3 text-center pt-6 sm:pt-10">
            {/* Friendly Bot Avatar Circle */}
            <div className="w-16 h-16 rounded-full bg-[var(--color-accent-2-100)] text-[var(--color-accent-2-700)] flex items-center justify-center shadow-xs">
              <Bot className="w-8 h-8" />
            </div>

            {/* Welcome Title & Desc */}
            <h2 className="font-heading text-xl sm:text-2xl text-[var(--color-text)] m-0">
              {t.welcomeTitle}
            </h2>
            <p className="m-0 text-xs sm:text-[13.5px] text-[var(--color-neutral-700)] leading-relaxed max-w-lg">
              {t.welcomeDesc}
            </p>

            {/* Quick Prompt / Topic Chips */}
            <div className="flex gap-2 flex-wrap justify-center mt-2 max-w-xl">
              {topic.sampleQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSendMessage(q)}
                  className="tag tag-outline cursor-pointer text-xs py-1.5 px-3.5 hover:bg-[var(--color-accent-100)] transition-all font-body text-left"
                >
                  <HelpCircle className="w-3 h-3 inline mr-1 text-[var(--color-accent)]" />
                  <span>{q}</span>
                </button>
              ))}
              {topic.tags.map((tag, idx) => (
                <button
                  key={`tag-${idx}`}
                  type="button"
                  onClick={() => setInputText(tag.replace('#', '') + ' ')}
                  className="tag tag-neutral cursor-pointer text-xs py-1.5 px-3 hover:bg-[var(--color-neutral-200)] transition-all"
                >
                  #{tag.replace('#', '')}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-3xl ${
                msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-none text-white shadow-2xs ${
                  msg.role === 'user'
                    ? 'bg-[var(--color-accent-700)]'
                    : 'bg-gradient-to-br from-[var(--color-accent-2-600)] to-[var(--color-accent-2-800)]'
                }`}
              >
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`rounded-[24px] p-4 text-sm transition-all ${
                  msg.role === 'user'
                    ? 'bg-[var(--color-accent)] text-white rounded-tr-xs shadow-xs max-w-lg'
                    : 'bg-[var(--color-neutral-100)] border border-[var(--color-neutral-200)] rounded-tl-xs shadow-xs flex-1'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="m-0 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div>
                    {renderFormattedContent(msg.content, msg.citations)}

                    {/* Citations List if present */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[var(--color-divider)]">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--color-neutral-700)] mb-2">
                          <BookOpen className="w-3.5 h-3.5 text-[var(--color-accent-600)]" />
                          <span>{t.sourcesHeader} ({msg.citations.length} 篇):</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c) => (
                            <button
                              key={c.citation_id}
                              type="button"
                              onClick={() => setSelectedCitation(c)}
                              className="text-xs bg-[var(--color-surface)] border border-[var(--color-divider)] hover:border-[var(--color-accent)] px-2.5 py-1 rounded-full text-[var(--color-text)] hover:text-[var(--color-accent-700)] transition-colors flex items-center gap-1 shadow-2xs cursor-pointer"
                            >
                              <span className="font-bold text-[var(--color-accent-700)]">[{c.citation_id}]</span>
                              <span className="truncate max-w-[200px]">{c.title}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Footer: Timestamp & Copy button */}
                    <div className="flex items-center justify-between mt-3 pt-2 text-[11px] text-[var(--color-neutral-500)]">
                      <span>{msg.timestamp}</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="btn btn-ghost text-[11px] px-2 py-0.5"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="w-3 h-3 text-[var(--color-accent-2-700)]" />
                            <span className="text-[var(--color-accent-2-700)] font-bold">{t.copiedBtn}</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>{t.copyBtn}</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Streaming Loading Indicator */}
        {loading && (
          <div className="flex gap-3 max-w-2xl">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--color-accent-2-600)] to-[var(--color-accent-2-800)] flex items-center justify-center flex-none text-white shadow-2xs">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-[var(--color-neutral-100)] border border-[var(--color-neutral-200)] rounded-[24px] rounded-tl-xs p-4 flex items-center gap-2.5">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce [animation-delay:0.4s]" />
              </div>
              <span className="text-xs text-[var(--color-neutral-600)]">
                {t.searchingText}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Citation Modal / Drawer */}
      {selectedCitation && (
        <div className="absolute inset-x-0 bottom-0 bg-[var(--color-bg)] border-t-2 border-[var(--color-accent)] p-4 shadow-xl z-30 transition-all max-h-72 overflow-y-auto animate-fade-up">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="tag tag-accent text-xs font-bold">
                [{selectedCitation.citation_id}] 引用來源
              </span>
              <h4 className="font-heading font-bold text-[var(--color-text)] text-sm m-0">
                {selectedCitation.title}
              </h4>
            </div>
            <button
              type="button"
              onClick={() => setSelectedCitation(null)}
              className="btn btn-icon btn-ghost text-[var(--color-neutral-600)]"
              aria-label="關閉來源"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="bg-[var(--color-surface)] rounded-[var(--radius-md)] p-3 border border-[var(--color-divider)] text-xs text-[var(--color-text)] leading-relaxed font-mono whitespace-pre-wrap">
            {selectedCitation.snippet || '（該篇政策文獻已作為整體 Grounding 依據）'}
          </div>
          {selectedCitation.link && (
            <div className="mt-2 flex justify-end">
              <span className="text-[11px] text-[var(--color-neutral-500)] truncate">
                來源路徑: {selectedCitation.link}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Bottom Input Bar */}
      <div className="flex-none border-t border-[var(--color-neutral-200)] p-4 sm:px-6 bg-[var(--color-bg)] flex flex-col gap-1.5">
        <form
          onSubmit={handleSubmit}
          className="flex gap-2.5 items-center max-w-[820px] w-full mx-auto"
        >
          <input
            className="input flex-1"
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder={t.inputPlaceholder}
            disabled={loading}
            style={{
              minHeight: '42px',
              paddingInline: '18px',
              backgroundColor: 'var(--color-surface)',
              borderColor: 'var(--color-divider)',
              color: 'var(--color-text)'
            }}
          />
          <button
            type="submit"
            disabled={!inputText.trim() || loading}
            className="btn btn-primary btn-icon flex-none shadow-sm"
            aria-label="發送問題"
          >
            <Send className="icn" />
          </button>
        </form>
        <div className="text-[11px] text-[var(--color-neutral-500)] text-center">
          {t.multilingualNote}
        </div>
      </div>
    </div>
  );
};
