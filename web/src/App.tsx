import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { TopicDrawer } from './components/TopicDrawer';
import { ChatView } from './components/ChatView';
import { Topic, ChatMessage, GovernanceDocument, Citation, LanguageCode } from './types';
import { STRINGS, INITIAL_TOPICS } from './i18n';
import { Layers, FlaskConical } from 'lucide-react';

export default function App() {
  const [lang, setLang] = useState<LanguageCode>('zh');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState<'topics' | 'analysis'>('topics');
  const [topics, setTopics] = useState<Topic[]>(INITIAL_TOPICS);
  const [selectedTopicId, setSelectedTopicId] = useState<string>(INITIAL_TOPICS[0].id);
  const [documents, setDocuments] = useState<GovernanceDocument[]>([]);
  const [messagesByTopic, setMessagesByTopic] = useState<Record<string, ChatMessage[]>>({});
  const [loading, setLoading] = useState(false);

  const t = STRINGS[lang] || STRINGS.zh;

  // 1. Fetch Topics & Document Metadata on Mount
  useEffect(() => {
    fetch('/api/topics')
      .then((res) => res.json())
      .then((data: Topic[]) => {
        if (Array.isArray(data) && data.length > 0) {
          // Merge API topics with styling tokens from INITIAL_TOPICS
          const merged = data.map((apiTopic) => {
            const fallback = INITIAL_TOPICS.find((it) => it.id === apiTopic.id);
            return {
              ...fallback,
              ...apiTopic,
              icon: fallback?.icon || 'shield',
              bg: fallback?.bg || 'var(--color-neutral-100)',
              border: fallback?.border || 'var(--color-neutral-200)',
              iconBg: fallback?.iconBg || 'var(--color-neutral-700)',
              iconFg: fallback?.iconFg || '#fff',
            };
          });
          setTopics(merged);
          setSelectedTopicId(merged[0].id);
        }
      })
      .catch((err) => console.log('Using built-in topics fallback:', err));

    fetch('/api/documents/list')
      .then((res) => res.json())
      .then((docs: GovernanceDocument[]) => {
        if (Array.isArray(docs)) setDocuments(docs);
      })
      .catch((err) => console.log('Failed to fetch doc list:', err));
  }, []);

  const currentTopic = topics.find((tp) => tp.id === selectedTopicId) || topics[0];
  const currentMessages = messagesByTopic[selectedTopicId] || [];

  const handleSelectTopic = (id: string) => {
    setSelectedTopicId(id);
    setDrawerOpen(false);
  };

  const handleOpenTopics = () => {
    setDrawerTab('topics');
    setDrawerOpen(true);
  };

  const handleOpenAnalysis = () => {
    setDrawerTab('analysis');
    setDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setDrawerOpen(false);
  };

  const handleLangChange = (newLang: LanguageCode) => {
    setLang(newLang);
  };

  const handleClearHistory = () => {
    setMessagesByTopic((prev) => ({
      ...prev,
      [selectedTopicId]: [],
    }));
  };

  // 2. Handle Send Message with SSE Streaming
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsgId = 'u-' + Date.now();
    const assistantMsgId = 'a-' + Date.now();
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: text,
      timestamp: nowTime,
    };

    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      citations: [],
      timestamp: nowTime,
      isStreaming: true,
    };

    // Append user & empty assistant message
    setMessagesByTopic((prev) => ({
      ...prev,
      [selectedTopicId]: [...(prev[selectedTopicId] || []), userMsg, assistantMsg],
    }));

    setLoading(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          topic_id: selectedTopicId,
          city: '台北',
          language: lang === 'zh' ? 'zh-TW' : lang,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let collectedCitations: Citation[] = [];

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const rawChunk = decoder.decode(value, { stream: true });
          const lines = rawChunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.substring(6));
                if (eventData.type === 'sources') {
                  collectedCitations = eventData.sources || [];
                  setMessagesByTopic((prev) => {
                    const topicMsgs = [...(prev[selectedTopicId] || [])];
                    const target = topicMsgs.find((m) => m.id === assistantMsgId);
                    if (target) target.citations = collectedCitations;
                    return { ...prev, [selectedTopicId]: topicMsgs };
                  });
                } else if (eventData.type === 'chunk') {
                  accumulatedText += eventData.text || '';
                  setMessagesByTopic((prev) => {
                    const topicMsgs = [...(prev[selectedTopicId] || [])];
                    const target = topicMsgs.find((m) => m.id === assistantMsgId);
                    if (target) target.content = accumulatedText;
                    return { ...prev, [selectedTopicId]: topicMsgs };
                  });
                } else if (eventData.type === 'done') {
                  // Completed
                }
              } catch {
                // Ignore partial JSON parse errors
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Streaming error:', err);
      setMessagesByTopic((prev) => {
        const topicMsgs = [...(prev[selectedTopicId] || [])];
        const target = topicMsgs.find((m) => m.id === assistantMsgId);
        if (target) {
          target.content =
            target.content ||
            `連線檢索時發生提示：${err.message || '請稍後重試'}。您可以點選建議問題重新發問。`;
        }
        return { ...prev, [selectedTopicId]: topicMsgs };
      });
    } finally {
      setLoading(false);
      setMessagesByTopic((prev) => {
        const topicMsgs = [...(prev[selectedTopicId] || [])];
        const target = topicMsgs.find((m) => m.id === assistantMsgId);
        if (target) target.isStreaming = false;
        return { ...prev, [selectedTopicId]: topicMsgs };
      });
    }
  };

  return (
    <div className="flex flex-col h-screen min-h-[640px] bg-[var(--color-bg)] text-[var(--color-text)] font-body overflow-hidden">
      {/* Top Navigation Bar */}
      <Header
        t={t}
        lang={lang}
        onLangChange={handleLangChange}
        documentCount={documents.length || 22}
      />

      {/* Main Body Workspace */}
      <div className="flex-1 flex min-h-0 relative">
        {/* Left Action Rail (84px) */}
        <nav
          aria-label="快捷側欄導航"
          className="flex-none w-[84px] flex flex-col items-center gap-2 py-4 px-2 border-r border-[var(--color-neutral-200)] bg-[var(--color-neutral-100)] select-none z-10"
        >
          <button
            type="button"
            onClick={handleOpenTopics}
            className={`w-full border-none rounded-[var(--radius-lg)] py-2.5 px-1 flex flex-col items-center gap-1 cursor-pointer font-body transition-colors ${
              drawerOpen && drawerTab === 'topics'
                ? 'bg-[var(--color-accent-100)] text-[var(--color-accent-700)] font-bold shadow-2xs'
                : 'bg-transparent text-[var(--color-neutral-700)] hover:bg-[var(--color-neutral-200)]'
            }`}
            title={t.railTopics}
          >
            <Layers className="icn" />
            <span className="text-[10.5px] leading-tight text-center font-medium">
              {t.railTopics}
            </span>
          </button>

          <button
            type="button"
            onClick={handleOpenAnalysis}
            className={`w-full border-none rounded-[var(--radius-lg)] py-2.5 px-1 flex flex-col items-center gap-1 cursor-pointer font-body transition-colors ${
              drawerOpen && drawerTab === 'analysis'
                ? 'bg-[var(--color-accent-100)] text-[var(--color-accent-700)] font-bold shadow-2xs'
                : 'bg-transparent text-[var(--color-neutral-700)] hover:bg-[var(--color-neutral-200)]'
            }`}
            title={t.railAnalysis}
          >
            <FlaskConical className="icn" />
            <span className="text-[10.5px] leading-tight text-center font-medium">
              {t.railAnalysis}
            </span>
          </button>
        </nav>

        {/* Slide-out Drawer */}
        <TopicDrawer
          t={t}
          topics={topics}
          selectedTopicId={selectedTopicId}
          onSelectTopic={handleSelectTopic}
          isOpen={drawerOpen}
          activeTab={drawerTab}
          onTabChange={setDrawerTab}
          onClose={handleCloseDrawer}
        />

        {/* Main Chat Workspace */}
        <ChatView
          t={t}
          topic={currentTopic}
          messages={currentMessages}
          loading={loading}
          onSendMessage={handleSendMessage}
          onClearHistory={handleClearHistory}
          onOpenTopics={handleOpenTopics}
        />
      </div>
    </div>
  );
}
