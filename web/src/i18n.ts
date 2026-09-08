import { LanguageCode, Topic } from './types';

export interface UIStrings {
  brand: string;
  brandSub: string;
  docCount: string;
  liveTag: string;
  railTopics: string;
  railAnalysis: string;
  topicsHint: string;
  analysisHint: string;
  currentBadge: string;
  supportLabel: string;
  riskLabel: string;
  focusLabel: string;
  switchBtn: string;
  welcomeTitle: string;
  welcomeDesc: string;
  inputPlaceholder: string;
  multilingualNote: string;
  restartBtn: string;
  copyBtn: string;
  copiedBtn: string;
  sourcesHeader: string;
  searchingText: string;
}

export const STRINGS: Record<LanguageCode, UIStrings> = {
  zh: {
    brand: 'AI 治理政策顧問系統',
    brandSub: '基於 AI 治理政策訪談報告的知識顧問',
    docCount: '已載入 22 份政策與訪談文獻',
    liveTag: '線上即時問答',
    railTopics: '焦點專題',
    railAnalysis: '核心剖析',
    topicsHint: '點擊專題切換探討領域',
    analysisHint: '各專題的核心焦點與支持/風險視角',
    currentBadge: '目前對話',
    supportLabel: '推動效益與支持視角',
    riskLabel: '實務挑戰與風險顧慮',
    focusLabel: '當前對話焦點：',
    switchBtn: '切換焦點',
    welcomeTitle: 'AI 治理政策與訪談知識顧問',
    welcomeDesc: '您可直接提問任何關於城市導入 AI 基礎設施規劃，或生成式 AI 使用指引等政策議題。',
    inputPlaceholder: '輸入你的問題……',
    multilingualNote: '支援聯合國六大官方語言及更多語言提問',
    restartBtn: '重新開始',
    copyBtn: '複製回答',
    copiedBtn: '已複製',
    sourcesHeader: '檢索引用政策文獻',
    searchingText: '正在檢索 Vertex AI Search 並整合政策文獻...'
  },
  en: {
    brand: 'Taipei City AI Governance Advisor',
    brandSub: 'Vertex AI Search policy retrieval & executive interview analysis',
    docCount: '22 policy & interview documents loaded',
    liveTag: 'Live Q&A online',
    railTopics: 'Focus Topics',
    railAnalysis: 'Core Analysis',
    topicsHint: 'Click a topic to switch focus area',
    analysisHint: 'Core focus and support/risk perspectives per topic',
    currentBadge: 'Active',
    supportLabel: 'Benefits & Support Perspective',
    riskLabel: 'Risks & Challenges',
    focusLabel: 'Current focus:',
    switchBtn: 'Switch topic',
    welcomeTitle: 'Taipei City AI Governance Knowledge Advisor',
    welcomeDesc: 'Ask anything about the 1999 hotline AI adoption, department interviews, DOIT infrastructure planning, or generative AI usage guidelines.',
    inputPlaceholder: 'Type your question…',
    multilingualNote: 'Supports questions in Chinese, English, Japanese and more',
    restartBtn: 'Restart',
    copyBtn: 'Copy answer',
    copiedBtn: 'Copied',
    sourcesHeader: 'Cited policy documents',
    searchingText: 'Searching Vertex AI Search and synthesizing policy documents...'
  },
  ja: {
    brand: '台北市 AI ガバナンス政策アドバイザー',
    brandSub: 'Vertex AI Search による政策検索と幹部インタビュー分析',
    docCount: '22件の政策・インタビュー資料を読込済み',
    liveTag: 'リアルタイムQ&A',
    railTopics: '特集トピック',
    railAnalysis: 'コア分析',
    topicsHint: 'クリックしてトピックを切り替え',
    analysisHint: '各トピックの核心と支持/リスク視点',
    currentBadge: '現在',
    supportLabel: '推進効果と支持の視点',
    riskLabel: '実務上の課題とリスク',
    focusLabel: '現在のフォーカス：',
    switchBtn: 'トピック切替',
    welcomeTitle: '台北市 AI ガバナンス知識アドバイザー',
    welcomeDesc: '1999ホットラインのAI導入、各局へのインタビュー、情報局の基盤整備、生成AI利用指針について質問できます。',
    inputPlaceholder: '質問を入力してください……',
    multilingualNote: '中国語・英語・日本語などでの質問に対応',
    restartBtn: 'やり直す',
    copyBtn: '回答をコピー',
    copiedBtn: 'コピー済み',
    sourcesHeader: '引用された政策文献',
    searchingText: 'Vertex AI Search を検索し政策文献を統合中...'
  },
  fr: {
    brand: 'Conseiller en gouvernance de l’IA de la ville de Taipei',
    brandSub: 'Recherche de politiques Vertex AI et analyse d’entretiens avec les dirigeants',
    docCount: '22 documents de politiques et d’entretiens chargés',
    liveTag: 'Q&R en direct',
    railTopics: 'Sujets phares',
    railAnalysis: 'Analyse clé',
    topicsHint: 'Cliquez sur un sujet pour changer de focus',
    analysisHint: 'Points clés et perspectives favorables/risques par sujet',
    currentBadge: 'Actif',
    supportLabel: 'Bénéfices et perspective favorable',
    riskLabel: 'Défis et risques',
    focusLabel: 'Sujet actuel :',
    switchBtn: 'Changer de sujet',
    welcomeTitle: 'Conseiller de connaissances en gouvernance de l’IA de Taipei',
    welcomeDesc: 'Posez vos questions sur l’adoption de l’IA par la ligne 1999, les entretiens avec les services, la planification d’infrastructure ou les directives sur l’IA générative.',
    inputPlaceholder: 'Saisissez votre question…',
    multilingualNote: 'Prend en charge les 6 langues officielles de l’ONU et plus',
    restartBtn: 'Recommencer',
    copyBtn: 'Copier',
    copiedBtn: 'Copié',
    sourcesHeader: 'Documents de politique cités',
    searchingText: 'Recherche dans Vertex AI Search et synthèse en cours...'
  },
  es: {
    brand: 'Asesor de gobernanza de IA de la ciudad de Taipéi',
    brandSub: 'Búsqueda de políticas con Vertex AI y análisis de entrevistas a directivos',
    docCount: '22 documentos de políticas y entrevistas cargados',
    liveTag: 'Preguntas y respuestas en vivo',
    railTopics: 'Temas destacados',
    railAnalysis: 'Análisis clave',
    topicsHint: 'Haga clic en un tema para cambiar el enfoque',
    analysisHint: 'Puntos clave y perspectivas de apoyo/riesgo por tema',
    currentBadge: 'Activo',
    supportLabel: 'Beneficios y perspectiva de apoyo',
    riskLabel: 'Desafíos y riesgos',
    focusLabel: 'Tema actual:',
    switchBtn: 'Cambiar tema',
    welcomeTitle: 'Asesor de conocimiento en gobernanza de IA de Taipéi',
    welcomeDesc: 'Pregunte sobre la adopción de IA en la línea 1999, entrevistas departamentales, planificación de infraestructura o directrices de IA generativa.',
    inputPlaceholder: 'Escriba su pregunta…',
    multilingualNote: 'Compatible con los 6 idiomas oficiales de la ONU y más',
    restartBtn: 'Reiniciar',
    copyBtn: 'Copiar',
    copiedBtn: 'Copiado',
    sourcesHeader: 'Documentos de política citados',
    searchingText: 'Buscando en Vertex AI Search y sintetizando documentos...'
  },
  ru: {
    brand: 'Советник по управлению ИИ города Тайбэй',
    brandSub: 'Поиск политик Vertex AI и анализ интервью с руководителями',
    docCount: 'Загружено 22 документа политик и интервью',
    liveTag: 'Онлайн Q&A',
    railTopics: 'Ключевые темы',
    railAnalysis: 'Ключевой анализ',
    topicsHint: 'Нажмите на тему, чтобы переключить фокус',
    analysisHint: 'Ключевые аспекты и точки зрения по каждой теме',
    currentBadge: 'Активна',
    supportLabel: 'Преимущества и поддержка',
    riskLabel: 'Риски и проблемы',
    focusLabel: 'Текущая тема:',
    switchBtn: 'Сменить тему',
    welcomeTitle: 'Консультант по знаниям управления ИИ Тайбэя',
    welcomeDesc: 'Задавайте вопросы о внедрении ИИ на линии 1999, интервью с ведомствами, планировании инфраструктуры или рекомендациях по генеративному ИИ.',
    inputPlaceholder: 'Введите ваш вопрос…',
    multilingualNote: 'Поддерживает 6 официальных языков ООН и другие',
    restartBtn: 'Начать заново',
    copyBtn: 'Копировать',
    copiedBtn: 'Скопировано',
    sourcesHeader: 'Цитируемые документы',
    searchingText: 'Поиск в Vertex AI Search и анализ документов...'
  },
  ar: {
    brand: 'مستشار حوكمة الذكاء الاصطناعي لمدينة تايبيه',
    brandSub: 'بحث سياسات Vertex AI وتحليل مقابلات المسؤولين',
    docCount: 'تم تحميل 22 وثيقة سياسات ومقابلات',
    liveTag: 'أسئلة وأجوبة مباشرة',
    railTopics: 'المواضيع البارزة',
    railAnalysis: 'التحليل الأساسي',
    topicsHint: 'انقر على موضوع لتغيير التركيز',
    analysisHint: 'النقاط الأساسية ووجهات النظر الداعمة والمخاطر لكل موضوع',
    currentBadge: 'نشط',
    supportLabel: 'الفوائد ووجهة النظر الداعمة',
    riskLabel: 'التحديات والمخاطر',
    focusLabel: 'الموضوع الحالي:',
    switchBtn: 'تبديل الموضوع',
    welcomeTitle: 'مستشار معرفة حوكمة الذكاء الاصطناعي في تايبيه',
    welcomeDesc: 'اسأل عن اعتماد الذكاء الاصطناعي في خط 1999، ومقابلات الإدارات، وتخطيط البنية التحتية، أو إرشادات الذكاء الاصطناعي التوليدي.',
    inputPlaceholder: 'اكتب سؤالك…',
    multilingualNote: 'يدعم لغات الأمم المتحدة الرسمية الست وأكثر',
    restartBtn: 'إعادة البدء',
    copyBtn: 'نسخ الإجابة',
    copiedBtn: 'تم النسخ',
    sourcesHeader: 'وثائق السياسات المرجعية',
    searchingText: 'جارٍ البحث في Vertex AI Search وتلخيص الوثائق...'
  }
};

export const INITIAL_TOPICS: Topic[] = [
  {
    id: 'taipei-1999-ai',
    category: '市民服務與智慧客服',
    title: '1999 市民當家熱線導入 AI 效益與評估',
    description: '深入剖析台北市 1999 市民熱線導入語音辨識、意圖分類與 AI 客服之效益研究，以及研考會話應答品質與第一線挑戰。',
    tags: ['1999市民熱線', '研考會', 'AI語音客服'],
    documentsCount: 5,
    icon: 'phone',
    bg: 'var(--color-accent-100)',
    border: 'var(--color-accent-500)',
    iconBg: 'var(--color-accent-500)',
    iconFg: '#fff',
    sampleQuestions: [
      '台北市 1999 導入 AI 的效益評估研究主要結論與建議是什麼？',
      '研考會話務管理組蔡組長在訪談中提到哪些導入 AI 的實務挑戰與局限？',
      '1999 熱線導入 AI 技術後，話務人員的角色發生了什麼轉變？'
    ],
    keyCruxes: [
      {
        title: 'AI 效益 vs. 真人情感撫慰的不可替代性',
        description: 'AI 能夠快速處理重複性市政查詢與派工，但市民撥打 1999 常伴隨焦慮、不滿等情緒，AI 無法完全取代具備同理心之真人話務員。',
        proPoints: [
          '針對路燈不亮、垃圾清運等標準題型，AI 可 24 小時自動派工分流，顯著降低話務負載',
          '語音轉文字 (STT) 能大幅縮短話務人員記錄與打字時間，提升每通通話處理效率',
          '大數據與意圖分析有助於市府提前預警熱點民怨問題'
        ],
        conPoints: [
          '民眾在緊急或情緒激動時，聽到機器人語音容易引發更大反彈與抱怨',
          '複雜陳情案牽涉多個局處權責，現階段 AI 語意理解難以精準判斷跨局處歸屬',
          '部分長者或特定口音市民在語音辨識系統上面臨使用門檻'
        ]
      },
      {
        title: '市政動態知識庫的維護成本與正確性責任',
        description: '市政法規與各局處業務隨時變更，AI 訓練與知識庫維護若不及時，恐導致回答錯誤引發民怨爭議。',
        proPoints: [
          '透過統一的知識管理系統 (KMS) 結構化市政問答，促使各局處定期審查業務常見問題',
          '導入 RAG 檢索增強生成架構，回答時強制附帶法規來源出處，提高可信度'
        ],
        conPoints: [
          '各局處常未能即時同步最新法令或施工公告，導致 AI 回應產生幻覺或落後資訊',
          '若 AI 誤導民眾權益（如補助申請資格），行政責任與民怨承擔機制仍不明確'
        ]
      }
    ]
  },
  {
    id: 'taipei-genai-guidelines',
    category: '政策指引與治理規範',
    title: '臺北市政府使用人工智慧作業指引與生成式 AI 規範',
    description: '分析台北市政府頒布之 AI 作業指引，涵蓋資安防護、民眾個人資料保護、智慧財產權歸屬以及公務使用邊界。',
    tags: ['AI作業指引', '生成式AI', '資安防護'],
    documentsCount: 4,
    icon: 'shield',
    bg: 'var(--color-neutral-100)',
    border: 'var(--color-neutral-300)',
    iconBg: 'var(--color-neutral-700)',
    iconFg: '#fff',
    sampleQuestions: [
      '《臺北市政府使用人工智慧作業指引》對於公務員使用生成式 AI 有哪些核心規範與禁令？',
      '在公文撰寫與民眾陳情回覆中，指引如何規範人工審核 (Human-in-the-loop) 責任？',
      '市府如何防範公務機密與民眾個資因使用外部 AI 雲端模型而外洩？'
    ],
    keyCruxes: [
      {
        title: '機密資安防護 vs. 公務行政效率提升',
        description: '嚴格禁止公務機密與未公開資料上傳公開雲端 AI，與公務員渴望利用先進 LLM 提升文書與分析效率之間的拉鋸。',
        proPoints: [
          '嚴格規範可防止重大市政機密、人事資料或市民敏感個資流出',
          '建立地端/私有雲或政府專用通道模型，在確保資安前提下提供安全推論環境'
        ],
        conPoints: [
          '過於嚴格的禁令可能導致公務人員轉入「影子 AI」(Shadow AI) 私下使用個人帳號',
          '地端部署成本高昂且模型更新速度往往落後公開商業頂尖模型'
        ]
      },
      {
        title: 'AI 輔助 vs. 公務員最終法律與行政責任',
        description: '明確界定 AI 僅能作為「輔助工具」，所有對外正式公文、陳情答覆或行政處分均必須經由公務員實質審查並自行負責。',
        proPoints: [
          '堅守「人機協同 (Human-in-the-loop)」原則，避免演算法黑箱與行政卸責',
          '維護行政處分之合法性與公信力'
        ],
        conPoints: [
          '公務員若過度信任 AI 輸出而未仔細覆核，可能衍生行政瑕疵甚至國賠爭議',
          '需要持續對公務員進行 AI 素養與 Prompt 查核訓練'
        ]
      }
    ]
  },
  {
    id: 'taipei-bureau-interviews',
    category: '局處實務與首長訪談',
    title: '局處 AI 實務推動與首長訪談洞察',
    description: '彙整資訊局局長、人事處、觀傳局、都更處、自來水事業處等局處首長與主管之一線訪談，剖析推動歷程與挑戰。',
    tags: ['資訊局', '人事處', '觀傳局'],
    documentsCount: 10,
    icon: 'users',
    bg: 'var(--color-neutral-100)',
    border: 'var(--color-neutral-300)',
    iconBg: 'var(--color-neutral-700)',
    iconFg: '#fff',
    sampleQuestions: [
      '資訊局長在訪談中針對市府推動 AI 治理與基礎設施有何策略規劃？',
      '人事處在推廣公務人員 AI 賦能與教育訓練上遇到了哪些挑戰與規劃？',
      '觀傳局在實際應用 AI 於智慧旅遊與行銷時有哪些實務考量與經驗？'
    ],
    keyCruxes: [
      {
        title: '資訊局統一集中納管 vs. 各業務局處自主採購開發',
        description: '市府整體 AI 基礎設施、算力與共通 API 是否應由資訊局統一統籌，還是允許各局處依特定業務自行招標建置。',
        proPoints: [
          '統一平台可避免重複投資、確保資安標準一致，並發揮市府資料整合綜效',
          '有利於建立跨局處通用之 RAG 知識庫與共享基礎模型'
        ],
        conPoints: [
          '資訊局人力與專案排程有限，可能無法即時滿足各局處高度特化的業務時效需求',
          '業務局處最懂自身痛點，自主採購更能快速對接業界專屬解決方案'
        ]
      },
      {
        title: '公務體系內部文化與 AI 素養跨越',
        description: '公務員對新科技的抗拒、對出錯懲處的恐懼，以及人事處推動 AI 研習的普及度成效。',
        proPoints: [
          '人事處推動系統化培訓與案例競賽，逐步消除同仁對 AI 取代人力的焦慮',
          '透過標準作業 SOP 降低公務員使用 AI 的心理負擔'
        ],
        conPoints: [
          '部分資深同仁數位落差明顯，學習曲線較長',
          '缺乏明確的激勵機制促使基層公務員主動投入流程創新'
        ]
      }
    ]
  },
  {
    id: 'taipei-tpmo-smartcity',
    category: '概念驗證與公私協力',
    title: 'TPMO 台北智慧城市專案辦公室與概念驗證 (PoC)',
    description: '探討台北智慧城市專案辦公室 (TPMO) 採行之「1+7 智慧領域」架構、民間提案 PoC 試辦機制以及國際智慧城市評比經驗。',
    tags: ['TPMO', '智慧城市', 'PoC試辦'],
    documentsCount: 3,
    icon: 'leaf',
    bg: 'var(--color-accent-2-100)',
    border: 'var(--color-accent-2-500)',
    iconBg: 'var(--color-accent-2-500)',
    iconFg: '#fff',
    sampleQuestions: [
      'TPMO 在台北智慧城市推動架構中扮演什麼角色？其 1+7 領域機制如何運作？',
      '民間企業如何透過 TPMO 機制參與台北市的智慧城市與 AI 概念驗證 (PoC)？',
      '台北市在國際智慧城市評比中的優勢與持續改進方向為何？'
    ],
    keyCruxes: [
      {
        title: 'PoC 創新概念驗證到常態公務採購的銜接斷層 (Valley of Death)',
        description: '民間透過 TPMO 成功驗證的創新 AI 專案，在轉化為各局處正式預算招標時面臨採購法與預算編列門檻。',
        proPoints: [
          '由政府提供實體場域供民間零成本快速試錯，激發產業創新動能',
          '讓市府先驗證效益再決定是否大規模推廣，降低採購風險'
        ],
        conPoints: [
          '受限於政府採購法規，提案廠商完成 PoC 後仍須參與公開競標，無法直接獲取合約',
          '各局處若無後續長期維運預算支持，容易使優秀試辦方案淪為一次性展演'
        ]
      }
    ]
  }
];
