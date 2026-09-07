import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { TopicSelector } from './components/TopicSelector';
import { CruxCard } from './components/CruxCard';
import { ChatView } from './components/ChatView';
import { Topic, ChatMessage, GovernanceDocument } from './types';
import { Sparkles, BookOpen, Layers, ShieldCheck } from 'lucide-react';

const FALLBACK_TOPICS: Topic[] = [
  {
    id: "taipei-1999-ai",
    category: "市民服務與智慧客服",
    title: "1999 市民當家熱線導入 AI 效益與評估",
    description: "深入剖析台北市 1999 市民熱線導入語音辨識、意圖分類與 AI 客服之效益研究，以及研考會話務管理組在第一線的實務考量與限制。",
    tags: ["1999市民熱線", "研考會", "AI語音客服", "智慧派工", "情緒辨識", "效益評估"],
    documentsCount: 5,
    sampleQuestions: [
      "台北市 1999 導入 AI 的效益評估研究主要結論與建議是什麼？",
      "研考會話務管理組蔡組長在訪談中提到哪些導入 AI 的實務挑戰與局限？",
      "1999 熱線導入 AI 技術後，話務人員的角色發生了什麼轉變？"
    ],
    keyCruxes: [
      {
        title: "AI 自動化效益 vs. 真人同理心安撫的不可替代性",
        description: "AI 能快速派工重複性案件，但市民致電 1999 常伴隨焦慮情緒，AI 難以完全取代具備同理心之真人話務員。",
        proPoints: [
          "路燈不亮、垃圾清運等標準題型可 24 小時自動派工分流，顯著降低話務負載",
          "語音轉文字 (STT) 大幅縮短話務人員記錄與打字時間，提升每通處理效率",
          "大數據分析有助於市府提前預警熱點民怨問題"
        ],
        conPoints: [
          "民眾在緊急或情緒激動時，聽到機器人語音容易引發更大不滿",
          "複雜陳情案牽涉多局處權責，AI 語意理解難以精準判斷跨局處歸屬",
          "部分長者或特定口音市民在語音辨識上面臨操作門檻"
        ]
      },
      {
        title: "市政動態知識庫的維護成本與回答正確性責任",
        description: "市政法規與各局處業務時常變更，AI 訓練與知識庫維護若不及時，恐導致回答錯誤引發爭議。",
        proPoints: [
          "透過知識管理系統結構化市政問答，促使各局處定期審查業務常見問題",
          "導入 RAG 檢索增強生成架構，回答時強制附帶法規來源出處，提高公信力"
        ],
        conPoints: [
          "各局處未能即時同步最新法令或施工公告時，容易導致 AI 產生幻覺或落後資訊",
          "若 AI 誤導民眾權益（如補助資格），行政責任與民怨承擔機制仍不明確"
        ]
      }
    ]
  },
  {
    id: "taipei-genai-guidelines",
    category: "政策指引與治理規範",
    title: "臺北市政府使用人工智慧作業指引與生成式 AI 規範",
    description: "分析台北市政府頒布之 AI 作業指引，涵蓋資安防護、民眾個資保護、智財權歸屬及公務員使用界線。",
    tags: ["AI作業指引", "生成式AI", "資安防護", "個資隱私", "行政責任", "公文輔助"],
    documentsCount: 4,
    sampleQuestions: [
      "《臺北市政府使用人工智慧作業指引》對於公務員使用生成式 AI 有哪些核心規範與禁令？",
      "在公文撰寫與民眾陳情回覆中，指引如何規範人工審核 (Human-in-the-loop) 責任？",
      "市府如何防範公務機密與民眾個資因使用外部 AI 雲端模型而外洩？"
    ],
    keyCruxes: [
      {
        title: "機密資安防護 vs. 公務行政效率提升",
        description: "嚴格禁止公務機密與未公開資料上傳公開雲端 AI，與公務員渴望利用先進 LLM 提升效率之間的拉鋸。",
        proPoints: [
          "嚴格規範可防止重大市政機密、人事資料或市民個資流出",
          "建立地端/私有雲或政府專用通道模型，在確保資安前提下提供安全推論環境"
        ],
        conPoints: [
          "過於嚴格的禁令可能導致公務人員轉入「影子 AI」(Shadow AI) 私下使用個人帳號",
          "地端部署成本高昂且模型更新速度往往落後公開商業頂尖模型"
        ]
      },
      {
        title: "AI 輔助 vs. 公務員最終法律與行政責任",
        description: "明確界定 AI 僅能作為「輔助工具」，所有正式公文、陳情答覆均必須經由公務員實質審查並自行負責。",
        proPoints: [
          "堅守「人機協同 (Human-in-the-loop)」原則，避免演算法黑箱與行政卸責",
          "維護行政處分之合法性與公信力"
        ],
        conPoints: [
          "公務員若過度信任 AI 輸出而未仔細覆核，可能衍生行政瑕疵甚至國賠爭議",
          "需要持續對公務員進行 AI 素養與 Prompt 查核訓練"
        ]
      }
    ]
  },
  {
    id: "taipei-bureau-interviews",
    category: "局處實務與首長訪談",
    title: "局處 AI 實務推動與首長訪談洞察",
    description: "彙整資訊局局長、人事處、觀傳局、都更處、自來水處等局處主管訪談，剖析跨局處推動 AI 的痛點與轉型歷程。",
    tags: ["資訊局", "人事處", "觀傳局", "首長訪談", "組織文化", "AI素養培訓"],
    documentsCount: 10,
    sampleQuestions: [
      "資訊局長在訪談中針對市府推動 AI 治理與基礎設施有何策略規劃？",
      "人事處在推廣公務人員 AI 賦能與教育訓練上遇到了哪些挑戰與規劃？",
      "觀傳局在實際應用 AI 於智慧旅遊與行銷時有哪些實務考量與經驗？"
    ],
    keyCruxes: [
      {
        title: "資訊局統一集中納管 vs. 各業務局處自主採購開發",
        description: "市府整體 AI 基礎設施是否應由資訊局統籌，還是允許各局處依特定業務自行招標建置。",
        proPoints: [
          "統一平台可避免重複投資、確保資安標準一致，並發揮資料整合綜效",
          "有利於建立跨局處通用之 RAG 知識庫與共享基礎模型"
        ],
        conPoints: [
          "資訊局人力有限，可能無法即時滿足各局處高度特化的業務時效需求",
          "業務局處最懂自身業務，自主採購更能快速對接業界成熟方案"
        ]
      },
      {
        title: "公務體系內部文化與 AI 素養跨越",
        description: "公務員對新科技的抗拒、對出錯懲處的恐懼，以及人事處推動 AI 研習的成效。",
        proPoints: [
          "人事處推動系統化培訓與案例競賽，逐步消除同仁對 AI 取代人力的焦慮",
          "透過標準作業 SOP 降低公務員使用 AI 的心理負擔"
        ],
        conPoints: [
          "部分資深同仁數位落差明顯，學習曲線較長",
          "缺乏明確的激勵機制促使基層公務員主動投入流程創新"
        ]
      }
    ]
  },
  {
    id: "taipei-tpmo-smartcity",
    category: "概念驗證與公私協力",
    title: "TPMO 台北智慧城市專案辦公室與概念驗證 (PoC)",
    description: "探討台北智慧城市專案辦公室 (TPMO) 採行之「1+7 智慧領域」架構、民間提案 PoC 試辦機制及國際智慧城市經驗。",
    tags: ["TPMO", "智慧城市", "PoC試辦", "公私協力", "創新實驗場域", "國際評比"],
    documentsCount: 3,
    sampleQuestions: [
      "TPMO 在台北智慧城市推動架構中扮演什麼角色？其 1+7 領域機制如何運作？",
      "民間企業如何透過 TPMO 機制參與台北市的智慧城市與 AI 概念驗證 (PoC)？",
      "台北市在國際智慧城市評比中的優勢與持續改進方向為何？"
    ],
    keyCruxes: [
      {
        title: "PoC 創新概念驗證到常態公務採購的銜接斷層",
        description: "民間透過 TPMO 成功驗證的創新 AI 專案，在轉化為正式預算招標時面臨採購法規門檻。",
        proPoints: [
          "由政府提供實體場域供民間快速試錯，激發產業創新動能",
          "讓市府先驗證效益再決定是否大規模推廣，降低採購風險"
        ],
        conPoints: [
          "受限於政府採購法規，提案廠商完成 PoC 後仍須參與公開競標，無法直接獲取合約",
          "各局處若無後續長期維運預算支持，容易使試辦方案難以落地延續"
        ]
      }
    ]
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'documents' | 'cruxes'>('chat');
  const [topics, setTopics] = useState<Topic[]>(FALLBACK_TOPICS);
  const [selectedTopicId, setSelectedTopicId] = useState<string>(FALLBACK_TOPICS[0].id);
  const [documents, setDocuments] = useState<GovernanceDocument[]>([]);
  const [messagesByTopic, setMessagesByTopic] = useState<Record<string, ChatMessage[]>>({});
  const [loading, setLoading] = useState(false);

  // 1. Fetch Topics & Document Metadata on Mount
  useEffect(() => {
    fetch('/api/topics')
      .then((res) => res.json())
      .then((data: Topic[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setTopics(data);
          setSelectedTopicId(data[0].id);
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

  const currentTopic = topics.find((t) => t.id === selectedTopicId) || topics[0];
  const currentMessages = messagesByTopic[selectedTopicId] || [];

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
          language: 'zh-TW',
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let collectedCitations = [];

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
                // Ignore parse errors on partial frames
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
            `抱歉，連線檢索時發生提示：${err.message || '請稍後重試'}。您可以點選上方範例問題重新發問。`;
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

  const handleClearHistory = () => {
    setMessagesByTopic((prev) => ({
      ...prev,
      [selectedTopicId]: [],
    }));
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
      {/* Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        documentCount={documents.length || 22}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* TAB 1: AI 政策顧問對話 (Main Chat View) */}
        {activeTab === 'chat' && (
          <div className="space-y-6">
            {/* Topic Switcher Bar */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-bold text-slate-700 tracking-wide uppercase flex items-center space-x-1.5">
                  <Layers className="w-4 h-4 text-sky-600" />
                  <span>台北市 AI 治理焦點專題</span>
                </h2>
                <span className="text-xs text-slate-500">點擊專題切換探討領域</span>
              </div>
              <TopicSelector
                topics={topics}
                selectedTopicId={selectedTopicId}
                onSelectTopic={setSelectedTopicId}
              />
            </div>

            {/* Cruxes Preview for current topic */}
            {currentTopic.keyCruxes && currentTopic.keyCruxes.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                    📌 專題核心焦點與視角剖析
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentTopic.keyCruxes.map((crux, idx) => (
                    <CruxCard key={idx} crux={crux} index={idx} />
                  ))}
                </div>
              </div>
            )}

            {/* Chat Interface */}
            <ChatView
              topic={currentTopic}
              messages={currentMessages}
              loading={loading}
              onSendMessage={handleSendMessage}
              onClearHistory={handleClearHistory}
            />
          </div>
        )}

        {/* TAB 2: 政策文獻庫總覽 (Clean Document Overview) */}
        {activeTab === 'documents' && (
          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center space-x-2 text-sky-700 font-bold text-base mb-1">
                <BookOpen className="w-5 h-5" />
                <span>已索引之台北市 AI 治理政策文獻與訪談逐字稿</span>
              </div>
              <p className="text-xs text-slate-500">
                本系統已匯入 22 份台北市政府政策報告、研究評估與各局處長一線訪談資料，所有問答皆經由 Vertex AI Search 進行語意檢索與出處校驗。
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {(documents.length > 0 ? documents : [
                { filename: "1999市民熱線導入AI人工智慧最適方案評估研究.pdf", policy_domain: "市民客服", document_type: "研究報告", size_formatted: "1.2 MB", updated_at: "2026-09-07" },
                { filename: "臺北市政府使用人工智慧作業指引.docx", policy_domain: "法規指引", document_type: "作業指引", size_formatted: "45 KB", updated_at: "2026-09-07" },
                { filename: "20260504 北市府資訊局局長訪談.mp3", policy_domain: "局處訪談", document_type: "首長訪談逐字稿", size_formatted: "38.5 MB", updated_at: "2026-09-07" },
                { filename: "20260423_北市府人事處訪談.mp4", policy_domain: "局處訪談", document_type: "局處訪談逐字稿", size_formatted: "120 MB", updated_at: "2026-09-07" },
                { filename: "1130828-臺北智慧城市對外簡報(TPMO).pdf", policy_domain: "智慧城市", document_type: "簡報白皮書", size_formatted: "5.4 MB", updated_at: "2026-09-07" },
                { filename: "20260505研考會話務管理組蔡組長訪談.mp3", policy_domain: "1999客服", document_type: "業務訪談逐字稿", size_formatted: "28 MB", updated_at: "2026-09-07" }
              ]).map((doc: any, i: number) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs hover:shadow-sm transition-shadow">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-[10px] font-semibold bg-sky-50 text-sky-700 px-2 py-0.5 rounded border border-sky-200">
                      {doc.policy_domain || '市政治理'}
                    </span>
                    <span className="text-[10px] text-slate-400">{doc.size_formatted}</span>
                  </div>
                  <h4 className="font-bold text-slate-800 text-sm mb-1 line-clamp-2 leading-snug">
                    {doc.filename}
                  </h4>
                  <p className="text-xs text-slate-500 line-clamp-2 mt-1">
                    {doc.ai_summary || doc.document_type || '台北市政府政策研究與訪談材料'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: 核心爭點矩陣全貌 */}
        {activeTab === 'cruxes' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center space-x-2 text-indigo-700 font-bold text-base mb-1">
                <Sparkles className="w-5 h-5" />
                <span>台北市 AI 治理核心爭點全景矩陣</span>
              </div>
              <p className="text-xs text-slate-500">
                整理自台北市政府各局處首長訪談、研考會 1999 評估研究與作業指引，呈現公務機關推動 AI 治理時面臨的關鍵權衡。
              </p>
            </div>

            <div className="space-y-6">
              {topics.map((t) => (
                <div key={t.id} className="space-y-3">
                  <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
                    <span className="text-xs font-bold text-sky-800 bg-sky-100 px-2.5 py-0.5 rounded-full">
                      {t.category}
                    </span>
                    <h3 className="font-bold text-slate-900 text-sm sm:text-base">
                      {t.title}
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {t.keyCruxes.map((crux, idx) => (
                      <CruxCard key={idx} crux={crux} index={idx} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
