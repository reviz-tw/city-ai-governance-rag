import { useState, useRef, useEffect, FC, FormEvent, KeyboardEvent } from 'react';
import { Topic, ChatMessage, Citation } from '../types';
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
  topic: Topic;
  messages: ChatMessage[];
  loading: boolean;
  onSendMessage: (text: string) => void;
  onClearHistory: () => void;
}

export const ChatView: FC<ChatViewProps> = ({
  topic,
  messages,
  loading,
  onSendMessage,
  onClearHistory,
}) => {
  const [inputText, setInputText] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new message / streaming chunk
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || loading || isComposing) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 支援中文輸入法 (IME): 在選字/組字尚未結束時 (isComposing) 不觸發送出
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

  // Render basic markdown with formatted bold, lists, and citations
  const renderFormattedContent = (content: string, citations?: Citation[]) => {
    const lines = content.split('\n');
    return (
      <div className="space-y-2 text-sm leading-relaxed text-slate-800">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-2" />;

          // Headers
          if (line.startsWith('### ')) {
            return (
              <h4 key={idx} className="font-bold text-base text-slate-900 mt-3 mb-1">
                {line.replace('### ', '')}
              </h4>
            );
          }
          if (line.startsWith('## ')) {
            return (
              <h3 key={idx} className="font-bold text-lg text-slate-900 mt-4 mb-1">
                {line.replace('## ', '')}
              </h3>
            );
          }
          if (line.startsWith('# ')) {
            return (
              <h2 key={idx} className="font-extrabold text-xl text-slate-900 mt-4 mb-2">
                {line.replace('# ', '')}
              </h2>
            );
          }

          // Bullet lists
          if (line.startsWith('* ') || line.startsWith('- ')) {
            const clean = line.substring(2);
            return (
              <div key={idx} className="flex items-start space-x-2 pl-2">
                <span className="text-sky-500 font-bold mt-0.5">•</span>
                <div>{parseInlineFormatting(clean, citations)}</div>
              </div>
            );
          }

          // Numbered lists
          const numMatch = line.match(/^(\d+)\.\s(.*)/);
          if (numMatch) {
            return (
              <div key={idx} className="flex items-start space-x-2 pl-2">
                <span className="font-bold text-sky-600 text-xs mt-1">{numMatch[1]}.</span>
                <div>{parseInlineFormatting(numMatch[2], citations)}</div>
              </div>
            );
          }

          return <p key={idx}>{parseInlineFormatting(line, citations)}</p>;
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
          <strong key={i} className="font-semibold text-slate-900">
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
            onClick={() => citeObj && setSelectedCitation(citeObj)}
            className="inline-flex items-center mx-0.5 px-1.5 py-0.2 rounded text-[11px] font-bold bg-sky-100 text-sky-800 hover:bg-sky-200 border border-sky-300 transition-colors"
            title={citeObj ? `查看引用來源: ${citeObj.title}` : `引用來源 [${citeId}]`}
          >
            [{citeId}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden relative">
      {/* Top Banner / Topic context */}
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2 truncate">
          <span className="p-1.5 rounded-lg bg-sky-100 text-sky-700">
            <Sparkles className="w-4 h-4" />
          </span>
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            當前對話焦點:
          </span>
          <span className="text-xs sm:text-sm font-bold text-slate-800 truncate">
            {topic.title}
          </span>
        </div>

        {messages.length > 0 && (
          <button
            onClick={onClearHistory}
            className="flex items-center space-x-1 text-xs text-slate-500 hover:text-red-600 transition-colors px-2 py-1 rounded hover:bg-slate-200/50"
            title="清除對話紀錄"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">重新開始</span>
          </button>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto text-center py-8">
            <div className="w-14 h-14 rounded-2xl bg-sky-100 text-sky-600 flex items-center justify-center mb-4 shadow-sm">
              <Bot className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">
              台北市 AI 治理政策與訪談知識顧問
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 mb-6 max-w-lg leading-relaxed">
              您可直接提問任何關於台北市政府 1999 客服導入 AI、各局處推動訪談、資訊局基礎設施規劃，或生成式 AI 使用指引等政策議題。
            </p>

            {/* Quick Prompt Chips */}
            <div className="w-full text-left bg-slate-50 border border-slate-200 rounded-xl p-4">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-600 mb-3">
                <HelpCircle className="w-4 h-4 text-sky-600" />
                <span>建議焦點提問（點擊直接發送）:</span>
              </div>
              <div className="space-y-2">
                {topic.sampleQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendMessage(q)}
                    className="w-full text-left text-xs sm:text-sm p-2.5 rounded-lg bg-white border border-slate-200 hover:border-sky-400 hover:bg-sky-50/50 text-slate-700 hover:text-sky-900 transition-all flex items-center justify-between group shadow-2xs"
                  >
                    <span>{q}</span>
                    <Send className="w-3.5 h-3.5 text-slate-300 group-hover:text-sky-600 transition-colors ml-2 flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex space-x-3 max-w-4xl ${
                msg.role === 'user' ? 'ml-auto flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-white shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-slate-700'
                    : 'bg-gradient-to-tr from-sky-600 to-indigo-600'
                }`}
              >
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`relative rounded-2xl p-4 transition-all ${
                  msg.role === 'user'
                    ? 'bg-sky-600 text-white rounded-tr-none'
                    : 'bg-slate-50 border border-slate-200 rounded-tl-none flex-1'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div>
                    {renderFormattedContent(msg.content, msg.citations)}

                    {/* Citations List if present */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-200/80">
                        <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-600 mb-2">
                          <BookOpen className="w-3.5 h-3.5 text-sky-600" />
                          <span>檢索引用政策文獻 ({msg.citations.length} 篇):</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c) => (
                            <button
                              key={c.citation_id}
                              onClick={() => setSelectedCitation(c)}
                              className="text-xs bg-white border border-slate-200 hover:border-sky-400 px-2.5 py-1 rounded-md text-slate-700 hover:text-sky-800 transition-colors flex items-center space-x-1 shadow-2xs"
                            >
                              <span className="font-bold text-sky-600">[{c.citation_id}]</span>
                              <span className="truncate max-w-[200px]">{c.title}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions: Copy & Timestamp */}
                    <div className="flex items-center justify-between mt-3 pt-2 text-[11px] text-slate-400">
                      <span>{msg.timestamp}</span>
                      <button
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="flex items-center space-x-1 text-slate-500 hover:text-slate-800 px-2 py-0.5 rounded hover:bg-slate-200/60 transition-colors"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-600" />
                            <span className="text-emerald-600">已複製</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>複製回答</span>
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

        {/* Loading / Streaming Indicator */}
        {loading && (
          <div className="flex space-x-3 max-w-3xl">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center flex-shrink-0 text-white shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-none p-4 flex items-center space-x-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-sky-500 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-sky-500 animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 rounded-full bg-sky-500 animate-bounce [animation-delay:0.4s]" />
              </div>
              <span className="text-xs text-slate-500">
                正在檢索 Vertex AI Search 並整合政策文獻...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Citation Modal / Drawer */}
      {selectedCitation && (
        <div className="absolute inset-x-0 bottom-0 bg-white border-t-2 border-sky-500 p-4 shadow-xl z-20 transition-all max-h-64 overflow-y-auto">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded bg-sky-100 text-sky-800 font-bold text-xs">
                [{selectedCitation.citation_id}] 引用來源
              </span>
              <h4 className="font-bold text-slate-900 text-sm">
                {selectedCitation.title}
              </h4>
            </div>
            <button
              onClick={() => setSelectedCitation(null)}
              className="text-slate-400 hover:text-slate-600 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs text-slate-700 leading-relaxed font-mono whitespace-pre-wrap">
            {selectedCitation.snippet || '（該篇文獻已作為整體 Grounding 依據）'}
          </div>
          {selectedCitation.link && (
            <div className="mt-2 flex justify-end">
              <span className="text-[11px] text-slate-500 truncate">
                來源路徑: {selectedCitation.link}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Input Bar */}
      <div className="p-3 sm:p-4 bg-white border-t border-slate-200">
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <div className="flex-1 bg-slate-100 rounded-xl p-2 focus-within:ring-2 focus-within:ring-sky-500 focus-within:bg-white border border-slate-200 transition-all">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              placeholder="輸入政策問題（如：1999 客服導入 AI 的效益評估結論為何？Enter 發送，Shift+Enter 換行）..."
              rows={2}
              className="w-full bg-transparent border-0 resize-none text-xs sm:text-sm text-slate-800 focus:outline-hidden max-h-32 leading-relaxed"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={!inputText.trim() || loading}
            className="p-3 rounded-xl bg-sky-600 hover:bg-sky-700 disabled:bg-slate-200 text-white disabled:text-slate-400 transition-colors shadow-sm flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
