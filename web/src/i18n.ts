import { LanguageCode, Topic, Crux } from './types';

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
  docUnit: string;
  docsCountFormatted: (count: number) => string;
  currentTopicLabel: string;
  noCruxText: string;
  sourceCitationBadge: string;
  clearHistoryTitle: string;
  drawerCloseLabel: string;
  sendAriaLabel: string;
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
    searchingText: '正在檢索 Vertex AI Search 並整合政策文獻...',
    docUnit: '份相關文獻',
    docsCountFormatted: (count: number) => `📚 ${count} 份相關文獻`,
    currentTopicLabel: '當前專題：',
    noCruxText: '該專題目前尚無結構化爭點分析。',
    sourceCitationBadge: '引用來源',
    clearHistoryTitle: '清除當前對話紀錄',
    drawerCloseLabel: '關閉抽屜',
    sendAriaLabel: '發送問題',
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
    multilingualNote: 'Supports questions in Chinese, English, Japanese, French, Spanish, Russian, Arabic and more',
    restartBtn: 'Restart',
    copyBtn: 'Copy answer',
    copiedBtn: 'Copied',
    sourcesHeader: 'Cited policy documents',
    searchingText: 'Searching Vertex AI Search and synthesizing policy documents...',
    docUnit: 'related documents',
    docsCountFormatted: (count: number) => `📚 ${count} related documents`,
    currentTopicLabel: 'Current topic: ',
    noCruxText: 'No structured crux analysis available for this topic yet.',
    sourceCitationBadge: 'Citation Source',
    clearHistoryTitle: 'Clear current conversation history',
    drawerCloseLabel: 'Close drawer',
    sendAriaLabel: 'Send question',
  },
  ja: {
    brand: '台北市 AI ガバナンス政策アドバイザー',
    brandSub: 'Vertex AI Search による政策検索と幹部インタビュー分析',
    docCount: '22件の政策・インタビュー資料を読込済み',
    liveTag: 'リアルタイムQ&A',
    railTopics: '焦点トピック',
    railAnalysis: '核心分析',
    topicsHint: 'クリックしてトピックを切り替え',
    analysisHint: '各トピックの核心と支持/リスク視点',
    currentBadge: '対話中',
    supportLabel: '推進効果と支持の視点',
    riskLabel: '実務上の課題とリスク',
    focusLabel: '現在のフォーカス：',
    switchBtn: 'トピック切替',
    welcomeTitle: '台北市 AI ガバナンス知識アドバイザー',
    welcomeDesc: '1999ホットラインのAI導入、各局へのインタビュー、情報局の基盤整備、生成AI利用指針について質問できます。',
    inputPlaceholder: '質問を入力してください……',
    multilingualNote: '国連公用語（中・英・日・仏・西・露・アラビア語等）での質問に対応',
    restartBtn: 'やり直す',
    copyBtn: '回答をコピー',
    copiedBtn: 'コピー済み',
    sourcesHeader: '引用された政策文献',
    searchingText: 'Vertex AI Search を検索し政策文献を統合中...',
    docUnit: '件の関連資料',
    docsCountFormatted: (count: number) => `📚 関連資料 ${count} 件`,
    currentTopicLabel: '現在のトピック：',
    noCruxText: 'このトピックには構造化された論点分析がまだありません。',
    sourceCitationBadge: '引用元',
    clearHistoryTitle: '現在の対話履歴を消去',
    drawerCloseLabel: 'ドロワーを閉じる',
    sendAriaLabel: '質問を送信',
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
    searchingText: 'Recherche dans Vertex AI Search et synthèse en cours...',
    docUnit: 'documents associés',
    docsCountFormatted: (count: number) => `📚 ${count} documents associés`,
    currentTopicLabel: 'Sujet actuel : ',
    noCruxText: 'Aucune analyse des controverses disponible pour ce sujet pour le moment.',
    sourceCitationBadge: 'Source de citation',
    clearHistoryTitle: 'Effacer l’historique de conversation actuel',
    drawerCloseLabel: 'Fermer le tiroir',
    sendAriaLabel: 'Envoyer la question',
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
    searchingText: 'Buscando en Vertex AI Search y sintetizando documentos...',
    docUnit: 'documentos relacionados',
    docsCountFormatted: (count: number) => `📚 ${count} documentos relacionados`,
    currentTopicLabel: 'Tema actual: ',
    noCruxText: 'No hay análisis de controversias estructurado para este tema todavía.',
    sourceCitationBadge: 'Fuente citada',
    clearHistoryTitle: 'Borrar historial de conversación actual',
    drawerCloseLabel: 'Cerrar panel',
    sendAriaLabel: 'Enviar pregunta',
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
    searchingText: 'Поиск в Vertex AI Search и анализ документов...',
    docUnit: 'связанных документов',
    docsCountFormatted: (count: number) => `📚 ${count} связанных документов`,
    currentTopicLabel: 'Текущая тема: ',
    noCruxText: 'Структурированный анализ ключевых вопросов для этой темы пока отсутствует.',
    sourceCitationBadge: 'Источник цитаты',
    clearHistoryTitle: 'Очистить текущую историю переписки',
    drawerCloseLabel: 'Закрыть панель',
    sendAriaLabel: 'Отправить вопрос',
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
    searchingText: 'جارٍ البحث في Vertex AI Search وتلخيص الوثائق...',
    docUnit: 'وثيقة ذات صلة',
    docsCountFormatted: (count: number) => `📚 ${count} وثيقة ذات صلة`,
    currentTopicLabel: 'الموضوع الحالي: ',
    noCruxText: 'لا يوجد تحليل منظم للنقاط الجدلية لهذا الموضوع بعد.',
    sourceCitationBadge: 'المصدر المرجعي',
    clearHistoryTitle: 'مسح سجل المحادثة الحالي',
    drawerCloseLabel: 'إغلاق اللوحة',
    sendAriaLabel: 'إرسال السؤال',
  }
};

export interface TopicTranslation {
  category: string;
  title: string;
  description: string;
  tags: string[];
  sampleQuestions: string[];
  keyCruxes: Crux[];
}

export const TOPIC_TRANSLATIONS: Record<string, Partial<Record<LanguageCode, TopicTranslation>>> = {
  'taipei-1999-ai': {
    zh: {
      category: '市民服務與智慧客服',
      title: '1999 市民當家熱線導入 AI 效益與評估',
      description: '深入剖析台北市 1999 市民熱線導入語音辨識、意圖分類與 AI 客服之效益研究，以及研考會話務管理組在第一線的實務考量與限制。',
      tags: ['1999市民熱線', '研考會', 'AI語音客服', '智慧派工', '情緒辨識', '效益評估'],
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
            '針對路燈不亮、垃圾清運等標準化題型，AI 可 24 小時自動派工分流，顯著降低話務負載',
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
    en: {
      category: 'Citizen Service & Smart Contact Center',
      title: 'Taipei 1999 Citizen Hotline AI Adoption & Benefit Assessment',
      description: 'In-depth analysis of the feasibility and efficacy of speech recognition, intent classification, and AI customer service in Taipei 1999 hotline, alongside frontline operational limits from the Research, Development and Evaluation Commission (RDEC).',
      tags: ['1999 Hotline', 'RDEC', 'Voice AI', 'Smart Dispatch', 'Sentiment Analysis', 'Benefit Assessment'],
      sampleQuestions: [
        'What are the key conclusions and recommendations from the 1999 AI benefit assessment study?',
        'What practical challenges and limitations did RDEC Hotline Division Chief Tsai highlight in the interview?',
        'How has the role of frontline operators shifted with the introduction of AI technologies?'
      ],
      keyCruxes: [
        {
          title: 'AI Automation Efficiency vs. Irreplaceable Human Empathy',
          description: 'AI handles standardized city queries and automated ticket dispatch swiftly, but citizens dialing 1999 often bring emotional distress and anxiety that voicebots cannot genuinely empathize with.',
          proPoints: [
            'Automates 24/7 dispatch for recurring issues like streetlight outages and trash collection, drastically reducing call loads',
            'Speech-to-text (STT) cuts typing and record-keeping time, significantly accelerating handling per call',
            'Big data intent analytics helps city government detect and preempt hot-button civic complaints early'
          ],
          conPoints: [
            'Citizens in distress or anger react negatively when forced to interact with automated interactive bots',
            'Complex civic grievances cross multiple bureaus, challenging semantic categorization accuracy',
            'Elderly callers or dialect speakers face severe accessibility barriers with speech recognition'
          ]
        },
        {
          title: 'Dynamic Knowledge Base Maintenance Costs & Accountability for Errors',
          description: 'Municipal regulations and departmental procedures change continuously. Outdated knowledge bases risk hallucinations that mislead citizens and cause severe administrative disputes.',
          proPoints: [
            'Structured KMS forces periodic review and standardization of frequent municipal inquiries across all agencies',
            'RAG retrieval-augmented generation enforces verifiable regulatory citations with every generated answer'
          ],
          conPoints: [
            'Bureaus frequently fail to update real-time notices or regulations, causing AI misinformation',
            'Legal and administrative liability remains ambiguous when AI gives incorrect eligibility counsel for public welfare'
          ]
        }
      ]
    },
    ja: {
      category: '市民サービス・スマート窓口',
      title: '台北市 1999 市民ホットラインにおける AI 導入効果と評価',
      description: '台北市 1999 市民ホットラインにおける音声認識・意図分類・AI応対の導入効果研究、および研究考査委員会（研考会）話務管理組の現場視点と制約を徹底分析。',
      tags: ['1999ホットライン', '研考会', 'AI音声応対', '自動配分', '感情分析', '効果測定'],
      sampleQuestions: [
        '台北市1999へのAI導入効果評価研究における主な結論と提言は何ですか？',
        '研考会話務管理組の蔡組長はインタビューでどのような実務上の課題を挙げましたか？',
        'AI導入後、オペレーターの役割はどのように変化しましたか？'
      ],
      keyCruxes: [
        {
          title: 'AIの処理効率 vs. 生身のオペレーターによる共感・傾聴の不可欠性',
          description: 'AIは定型的な市政照会や業務割当を迅速化しますが、市民の電話には不安や不満が伴うことが多く、共感力を持った人間の対応を完全には代替できません。',
          proPoints: [
            '街灯故障やゴミ収集などの定型的な通報に対し、24時間自動受付・配分を行い負荷を劇的に低減',
            '音声テキスト化 (STT) によりメモ作成時間を短縮し、通話処理効率を向上',
            '通話データの意図分析により、市民の不満の急増トレンドを早期察知'
          ],
          conPoints: [
            '感情が高ぶっている市民がロボット音声に対応されると、さらなる苦情や反発を招くリスク',
            '複数局にまたがる複雑な請願の場合、AIの意図解析では所管の正確な判定が困難',
            '高齢者や方言話者にとって音声認識の認識精度に利用障壁が存在'
          ]
        },
        {
          title: '動的ナレッジベースの保守コストと誤答時の行政責任',
          description: '市政の規則や窓口業務は頻繁に改定されます。知識ベースの更新が遅れると誤答が発生し、市民の権利侵害や苦情につながります。',
          proPoints: [
            '統合ナレッジ管理システム (KMS) を構築することで、各局のFAQを定期点検・構造化',
            'RAG（検索拡張生成）の採用により、根拠法令の出典明記を義務付け信頼性を向上'
          ],
          conPoints: [
            '各局による最新法令や告知の同期漏れが発生しやすく、情報の陳腐化による誤回答リスクが残る',
            'AIが誤った補助金申請資格などを案内した場合の法的責任の所在が未整備'
          ]
        }
      ]
    },
    fr: {
      category: 'Services aux citoyens & Centre d’appel intelligent',
      title: 'Évaluation et bénéfices de l’intégration de l’IA sur la ligne citoyenne 1999',
      description: 'Analyse approfondie de la reconnaissance vocale, de la classification des intentions et des bénéfices de l’assistance IA sur la ligne 1999 de Taipei, ainsi que des retours d’expérience de la RDEC.',
      tags: ['Ligne 1999', 'RDEC', 'Assistance vocale IA', 'Routage intelligent', 'Analyse d’impact'],
      sampleQuestions: [
        'Quelles sont les conclusions majeures de l’étude d’impact de l’IA sur la ligne 1999 ?',
        'Quels défis pratiques ont été soulevés par le responsable de la gestion des appels de la RDEC ?',
        'Comment le rôle des opérateurs humains a-t-il évolué après le déploiement de l’IA ?'
      ],
      keyCruxes: [
        {
          title: 'Efficacité de l’IA vs. empathie humaine irremplaçable',
          description: 'L’IA traite rapidement les requêtes courantes, mais les citoyens appelant le 1999 expriment souvent de l’anxiété et de la colère que les robots ne peuvent pas apaiser.',
          proPoints: [
            'Prise en charge 24/7 des signalements standardisés (lampadaires, voirie), allégeant la charge de travail',
            'La transcription vocale en texte réduit le temps de saisie et accélère la clôture des tickets',
            'L’analyse prédictive des intentions permet d’anticiper les crises citoyennes'
          ],
          conPoints: [
            'Frustration accrue des appelants stressés face à des réponses automatisées',
            'Difficulté pour l’IA d’orienter avec précision les plaintes complexes interservices',
            'Barrières d’accessibilité pour les personnes âgées ou avec des accents régionaux'
          ]
        },
        {
          title: 'Coût de maintenance de la base de connaissances et responsabilité légale',
          description: 'Les réglementations municipales évoluent en continu. Une base de connaissances non actualisée expose la municipalité à des réponses erronées.',
          proPoints: [
            'Structuration des FAQ municipales à travers un système unifié de gestion des connaissances (KMS)',
            'L’architecture RAG garantit la citation explicite des textes officiels de référence'
          ],
          conPoints: [
            'Risque d’hallucinations si les services omettent de publier les dernières directives',
            'Flou juridique persistant sur la responsabilité administrative en cas de conseil erroné par l’IA'
          ]
        }
      ]
    },
    es: {
      category: 'Atención ciudadana y centro de contacto inteligente',
      title: 'Evaluación y beneficios de la adopción de IA en la línea ciudadana 1999',
      description: 'Análisis profundo sobre el reconocimiento de voz, clasificación de intenciones y atención con IA en la línea 1999 de Taipéi, junto con los límites prácticos expuestos por la Comisión de Investigación y Evaluación (RDEC).',
      tags: ['Línea 1999', 'RDEC', 'IA de voz', 'Despacho inteligente', 'Evaluación de beneficios'],
      sampleQuestions: [
        '¿Cuáles son las principales conclusiones del estudio de evaluación de IA en el 1999 de Taipéi?',
        '¿Qué desafíos y limitaciones prácticas destacó el jefe de gestión telefónica de la RDEC en la entrevista?',
        '¿Cómo ha cambiado el rol de los teleoperadores tras la implementación de la IA?'
      ],
      keyCruxes: [
        {
          title: 'Eficiencia de la IA vs. empatía humana insustituible',
          description: 'La IA agiliza trámites repetitivos y el enrutamiento de incidencias, pero los ciudadanos que llaman al 1999 a menudo experimentan angustia o enfado que un contestador no puede calmar.',
          proPoints: [
            'Atención automática 24/7 para quejas estándar (alumbrado, basuras), reduciendo drásticamente la saturación',
            'La transcripción de voz a texto (STT) reduce el tiempo de redacción de los operadores por llamada',
            'El análisis masivo de intenciones ayuda al gobierno a detectar quejas vecinales recurrentes de forma temprana'
          ],
          conPoints: [
            'Los ciudadanos con problemas urgentes sienten mayor frustración al interactuar con voces sintéticas',
            'Reclamaciones complejas que abarcan múltiples concejalías son difíciles de clasificar con precisión',
            'Barreras de accesibilidad para adultos mayores o ciudadanos con acentos regionales específicos'
          ]
        },
        {
          title: 'Costes de mantenimiento de la base de conocimiento y responsabilidad ante errores',
          description: 'Las normativas municipales cambian constantemente. Una base de datos desactualizada puede provocar alucinaciones de la IA y desinformar a la ciudadanía.',
          proPoints: [
            'Un sistema centralizado de gestión del conocimiento (KMS) obliga a actualizar periódicamente las FAQ',
            'La arquitectura RAG exige incluir fuentes normativas verificables en cada respuesta'
          ],
          conPoints: [
            'Falta de sincronización en tiempo real por parte de los departamentos, generando información obsoleta',
            'Incertidumbre jurídica sobre la responsabilidad administrativa en caso de que la IA dé información errónea sobre ayudas'
          ]
        }
      ]
    },
    ru: {
      category: 'Обслуживание граждан и умный контакт-центр',
      title: 'Внедрение ИИ на горячей линии 1999 Тайбэя: оценка эффективности',
      description: 'Глубокий анализ применения распознавания речи, классификации намерений и ИИ-операторов на линии 1999 Тайбэя, а также практические ограничения, отмеченные комиссией RDEC.',
      tags: ['Линия 1999', 'RDEC', 'Голосовой ИИ', 'Умная маршрутизация', 'Оценка эффективности'],
      sampleQuestions: [
        'Каковы основные выводы и рекомендации исследования внедрения ИИ на линии 1999?',
        'Какие практические трудности отметил начальник отдела обработки вызовов RDEC в интервью?',
        'Как изменилась роль операторов-людей после интеграции технологий ИИ?'
      ],
      keyCruxes: [
        {
          title: 'Эффективность ИИ vs. незаменимость человеческого сочувствия',
          description: 'ИИ быстро обрабатывает типовые запросы и заявки, но звонки на 1999 часто связаны со стрессом и недовольством, где необходима человеческая эмпатия.',
          proPoints: [
            'Круглосуточная автоматическая маршрутизация типовых заявок (освещение, вывоз мусора), снижающая нагрузку',
            'Преобразование речи в текст (STT) сокращает время документирования звонка оператором',
            'Анализ тональности и намерений позволяет заранее выявлять очаги недовольства горожан'
          ],
          conPoints: [
            'Граждане в критических ситуациях негативно реагируют на ответы голосового бота',
            'Сложные межведомственные жалобы вызывают ошибки автоматической категоризации',
            'Пожилые люди и граждане с нестандартным произношением сталкиваются с барьерами распознавания'
          ]
        },
        {
          title: 'Затраты на поддержку базы знаний и ответственность за неверные ответы',
          description: 'Городские нормативные акты регулярно меняются. Несвоевременное обновление базы знаний ведет к ошибкам и дезинформации.',
          proPoints: [
            'Единая система управления знаниями (KMS) структурирует регламенты всех департаментов',
            'Архитектура RAG обязывает систему указывать официальные ссылки на нормативные акты'
          ],
          conPoints: [
            'Задержка синхронизации данных от ведомств приводит к устаревшим ответам ИИ',
            'Отсутствие четких юридических механизмов ответственности за неверные консультации ИИ по льготам'
          ]
        }
      ]
    },
    ar: {
      category: 'خدمة المواطنين ومركز الاتصال الذكي',
      title: 'تقييم وفوائد تطبيق الذكاء الاصطناعي في خط خدمة المواطنين 1999',
      description: 'تحليل متعمق لدراسات الجدوى للتعرف على الصوت، وتصنيف النوايا، والمساعد الذكي في خط 1999 بتايبيه، إلى جانب التحديات الميدانية للجنة RDEC.',
      tags: ['خط 1999', 'لجنة RDEC', 'الذكاء الصوتي', 'التوزيع الذكي', 'تقييم الفوائد'],
      sampleQuestions: [
        'ما هي أبرز النتائج والتوصيات لدراسة تقييم فوائد الذكاء الاصطناعي في خط 1999؟',
        'ما هي التحديات والقيود العملية التي ذكرها رئيس قسم الاتصالات في مقابلته؟',
        'كيف تغير دور الموظفين البشريين بعد إدخال تقنيات الذكاء الاصطناعي؟'
      ],
      keyCruxes: [
        {
          title: 'كفاءة الذكاء الاصطناعي مقابل التعاطف الإنساني الذي لا غنى عنه',
          description: 'يعالج الذكاء الاصطناعي الاستفسارات الروتينية بسرعة، لكن اتصالات المواطنين غالباً ما تصاحبها مشاعر قلق وغضب تتطلب تعاطفاً بشرياً حقيقياً.',
          proPoints: [
            'توزيع آلي على مدار 24 ساعة للبلاغات النمطية كإنارة الشوارع والنظافة مما يقلل الضغط',
            'تحويل الصوت إلى نص (STT) يقلل وقت الكتابة والتوثيق للموظفين',
            'تحليل النوايا يساعد بلدية المدينة على رصد الشكاوى الشعبية المتكررة مبكراً'
          ],
          conPoints: [
            'شعور المواطنين بالاستياء عند الرد الآلي في الحالات الطارئة أو الغاضبة',
            'صعوبة تصنيف الشكاوى المعقدة التي تتقاطع فيها مسؤوليات عدة إدارات',
            'صعوبات استخدام لكبار السن أو أصحاب اللهجات غير المعتادة'
          ]
        },
        {
          title: 'تكاليف تحديث قاعدة المعرفة الديناميكية والمسؤولية عن الأخطاء',
          description: 'تتغير القوانين البلدية باستمرار، وعدم تحديث قاعدة المعرفة يؤدي إلى إجابات خاطئة تضلل المواطنين.',
          proPoints: [
            'نظام موحد لإدارة المعرفة (KMS) يضمن مراجعة وتحديث الأسئلة الشائعة للدوائر دورياً',
            'اعتماد تقنية RAG يفرض إرفاق نصوص اللوائح والمراجع مع كل إجابة لتعزيز الموثوقية'
          ],
          conPoints: [
            'تأخر بعض الإدارات في تحديث اللوائح يؤدي إلى توليد إجابات قديمة أو مضللة',
            'عدم وضوح المسؤولية الإدارية والقانونية في حال تقديم الذكاء الاصطناعي معلومات خاطئة للمواطنين'
          ]
        }
      ]
    }
  },

  'taipei-genai-guidelines': {
    zh: {
      category: '政策指引與治理規範',
      title: '臺北市政府使用人工智慧作業指引與生成式 AI 規範',
      description: '分析台北市政府頒布之 AI 作業指引，涵蓋資安防護、民眾個人資料保護、智慧財產權歸屬以及公務使用邊界。',
      tags: ['AI作業指引', '生成式AI', '資安防護', '個資隱私', '行政責任', '公文輔助'],
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
    en: {
      category: 'Policy Guidelines & Governance Standards',
      title: 'Taipei City Operational Guidelines for AI & Generative AI Governance',
      description: 'Comprehensive analysis of Taipei City’s official guidelines governing generative AI usage, focusing on information security, data privacy, IP ownership, and civil servant accountability boundaries.',
      tags: ['AI Guidelines', 'GenAI', 'InfoSec', 'Privacy', 'Civil Accountability', 'Official Docs'],
      sampleQuestions: [
        'What are the core rules and prohibitions for civil servants under Taipei’s AI Operational Guidelines?',
        'How do the guidelines enforce Human-in-the-loop oversight in drafting official documents and citizen replies?',
        'How does Taipei prevent leaks of confidential government data and citizen PII to external cloud models?'
      ],
      keyCruxes: [
        {
          title: 'Confidentiality & Data Security vs. Public Administrative Efficiency',
          description: 'Balancing the strict ban on uploading sensitive or non-public data to public cloud AI against civil servants’ eagerness to use advanced LLMs for rapid productivity.',
          proPoints: [
            'Strict redlines safeguard confidential city records, personnel files, and sensitive citizen PII from leaks',
            'Deploying on-premise or dedicated government cloud channels provides secure inference environments'
          ],
          conPoints: [
            'Excessive restrictions may drive staff toward unmonitored "Shadow AI" using personal devices',
            'Private cloud deployments entail high infrastructure costs and lag behind state-of-the-art commercial LLMs'
          ]
        },
        {
          title: 'AI Assistance vs. Ultimate Legal and Administrative Liability',
          description: 'Strictly defining AI as an auxiliary drafting tool while mandating that civil servants retain full substantive responsibility for all formal municipal outputs.',
          proPoints: [
            'Enforces the "Human-in-the-loop" principle to prevent algorithmic black boxes and administrative evasion',
            'Protects public credibility and legal validity of administrative sanctions and responses'
          ],
          conPoints: [
            'Complacency or blind trust in AI summaries may introduce subtle factual errors and state compensation liabilities',
            'Demands continuous citywide training on AI literacy and hallucination verification'
          ]
        }
      ]
    },
    ja: {
      category: '政策指針・ガバナンス規範',
      title: '台北市政府 人工知能（AI）利用作業指針と生成AI規範',
      description: '台北市政府が定めたAI運用ガイドラインの分析。情報セキュリティ保護、市民の個人情報保護、知的財産権の帰属、公務における利用限界を検証。',
      tags: ['AI作業指針', '生成AI', '情報セキュリティ', '個人情報保護', '行政責任', '公文書作成'],
      sampleQuestions: [
        '『台北市政府AI利用作業指針』における公務員の生成AI利用に関する禁止事項は何ですか？',
        '公文書や市民への回答作成において、指針は「人間による審査（Human-in-the-loop）」をどう定めていますか？',
        '外部の商用クラウドAIへの公務機密や個人情報の流出をどのように防止していますか？'
      ],
      keyCruxes: [
        {
          title: '機密情報セキュリティ vs. 公務の行政効率向上',
          description: '機密データや未公開資料のクラウドAI送信禁止と、最新LLMを活用して文書作成やデータ分析を効率化したい現場ニーズの対立。',
          proPoints: [
            '厳格な利用規程により重要機密や個人情報の外部流出を確実に防止',
            '政府専用チャネルやオンプレミスモデルの構築により、安全なAI推論環境を提供'
          ],
          conPoints: [
            '過度な規制は、職員が個人アカウントで利用する「シャドーAI」を誘発する恐れがある',
            'オンプレミス導入は高額な初期費用がかかり、最新商用モデルの性能進化に追従しにくい'
          ]
        },
        {
          title: 'AI補助 vs. 公務員の最終的な法的・行政的責任',
          description: 'AIはあくまで「補助ツール」であり、公式公文書や行政処分の内容に対する最終責任はすべて公務員自身が負う原則の確立。',
          proPoints: [
            '「ヒューマン・イン・ザ・ループ」を徹底し、ブラックボックス化と行政責任の放棄を防止',
            '行政処分の適法性と市民に対する公的信用を維持'
          ],
          conPoints: [
            'AI出力を過信して確認を怠った場合、行政瑕疵や国家賠償請求に発展するリスク',
            '公務員に対するプロンプト検証やAIリテラシー研修を継続的に実施する必要性'
          ]
        }
      ]
    },
    fr: {
      category: 'Directives politiques & Normes de gouvernance',
      title: 'Directives d’utilisation de l’IA et cadre de l’IA générative de Taipei',
      description: 'Analyse des directives municipales encadrant l’IA générative : cybersécurité, protection des données personnelles (RGPD local), propriété intellectuelle et responsabilité légale.',
      tags: ['Directives IA', 'IA générative', 'Cybersécurité', 'Vie privée', 'Responsabilité administrative'],
      sampleQuestions: [
        'Quelles sont les obligations et interdictions fondamentales pour les agents publics de Taipei ?',
        'Comment la supervision humaine (Human-in-the-loop) est-elle formalisée dans la rédaction administrative ?',
        'Quelles mesures protègent les secrets d’État et données personnelles contre les fuites vers les clouds tiers ?'
      ],
      keyCruxes: [
        {
          title: 'Cybersécurité & confidentialité vs. efficacité administrative',
          description: 'Équilibre entre l’interdiction formelle de téléverser des données confidentielles sur les LLMs commerciaux et le gain d’efficacité espéré par les agents.',
          proPoints: [
            'Protection rigoureuse des données sensibles et du patrimoine informationnel de la ville',
            'Mise en place d’infrastructures souveraines et de canaux sécurisés pour les administrations'
          ],
          conPoints: [
            'Risque de « Shadow AI » non régulé si les contraintes opérationnelles sont excessives',
            'Coût élevé des déploiements sur serveurs privés comparé à l’offre commerciale'
          ]
        },
        {
          title: 'Assistance par l’IA vs. responsabilité juridique de l’agent',
          description: 'L’IA reste un simple assistant ; l’agent public conserve l’entière responsabilité légale de chaque acte administratif émis.',
          proPoints: [
            'Respect strict du contrôle humain contre l’opacité algorithmique',
            'Préservation de la légalité et de la confiance du public dans l’administration'
          ],
          conPoints: [
            'Risque d’erreurs factuelles non détectées en cas de confiance excessive dans les réponses générées',
            'Nécessité de former en continu les agents à l’audit critique des réponses IA'
          ]
        }
      ]
    },
    es: {
      category: 'Directrices de política y estándares de gobernanza',
      title: 'Directrices de uso de IA y normativa sobre IA generativa de la ciudad de Taipéi',
      description: 'Análisis de las directrices de la ciudad de Taipéi sobre el uso de IA generativa: ciberseguridad, protección de datos personales, propiedad intelectual y límites de responsabilidad de los funcionarios.',
      tags: ['Directrices IA', 'IA Generativa', 'Ciberseguridad', 'Privacidad', 'Responsabilidad pública'],
      sampleQuestions: [
        '¿Cuáles son las principales normas y prohibiciones para los funcionarios según las directrices de Taipéi?',
        '¿Cómo regulan las directrices la supervisión humana (Human-in-the-loop) en la redacción de documentos oficiales?',
        '¿Cómo previene el gobierno la fuga de datos confidenciales y personales hacia modelos externos en la nube?'
      ],
      keyCruxes: [
        {
          title: 'Seguridad de la información y privacidad vs. eficiencia administrativa',
          description: 'La estricta prohibición de subir datos no públicos a modelos comerciales frente al interés de los funcionarios en agilizar sus tareas con LLMs avanzados.',
          proPoints: [
            'Las líneas rojas evitan fugas de secretos municipales y datos sensibles de los ciudadanos',
            'El despliegue en nubes privadas gubernamentales proporciona un entorno de inferencia seguro'
          ],
          conPoints: [
            'Prohibiciones excesivas pueden propiciar el uso informal de "Shadow AI" en cuentas personales',
            'Los despliegues propios son costosos y evolucionan más lento que los modelos comerciales punteros'
          ]
        },
        {
          title: 'Asistencia de la IA vs. responsabilidad legal y administrativa final',
          description: 'Definición de la IA estrictamente como herramienta de apoyo, manteniendo la responsabilidad legal en manos del funcionario firmante.',
          proPoints: [
            'Consolida el principio de supervisión humana frente a cajas negras algorítmicas',
            'Garantiza la validez jurídica y la confianza pública en los actos administrativos'
          ],
          conPoints: [
            'La confianza excesiva en los resúmenes de IA puede generar errores en resoluciones oficiales',
            'Requiere formación continua a los funcionarios en detección de alucinaciones e ingeniería de prompts'
          ]
        }
      ]
    },
    ru: {
      category: 'Политические директивы и стандарты управления',
      title: 'Регламент использования ИИ и стандарты генеративного ИИ мэрии Тайбэя',
      description: 'Анализ официальных руководств Тайбэя по использованию генеративного ИИ: информационная безопасность, защита персональных данных, интеллектуальная собственность и границы ответственности госслужащих.',
      tags: ['Руководство по ИИ', 'Генеративный ИИ', 'Инфобезопасность', 'Приватность', 'Ответственность'],
      sampleQuestions: [
        'Каковы основные правила и запреты для госслужащих согласно регламенту Тайбэя по ИИ?',
        'Как регламент определяет обязательный человеческий контроль (Human-in-the-loop) при составлении документов?',
        'Как город предотвращает утечку конфиденциальных данных и персональной информации в коммерческие облака?'
      ],
      keyCruxes: [
        {
          title: 'Информационная безопасность vs. повышение административной эффективности',
          description: 'Баланс между строгим запретом на загрузку конфиденциальных данных в публичные LLM и стремлением сотрудников повысить скорость работы.',
          proPoints: [
            'Четкие запреты предотвращают утечки закрытой служебной информации и данных граждан',
            'Развертывание локальных моделей или закрытых каналов обеспечивает безопасную среду вычислений'
          ],
          conPoints: [
            'Чрезмерные запреты провоцируют появление «теневого ИИ» (Shadow AI) с личных устройств',
            'Локальное развертывание требует значительных затрат и уступает ведущим облачным LLM'
          ]
        },
        {
          title: 'ИИ-помощник vs. персональная юридическая ответственность служащего',
          description: 'ИИ признается исключительно вспомогательным инструментом, а полную ответственность за любые официальные документы несет конкретный госслужащий.',
          proPoints: [
            'Соблюдение принципа контроля человеком исключает безответственность и «черные ящики» алгоритмов',
            'Обеспечение юридической чистоты и доверия к административным актам'
          ],
          conPoints: [
            'Слепое доверие выводам ИИ может приводить к административным ошибкам и судебным искам',
            'Необходимость регулярного обучения персонала фактчекингу и грамотной работе с промптами'
          ]
        }
      ]
    },
    ar: {
      category: 'إرشادات السياسات ومعايير الحوكمة',
      title: 'دليل العمل باستخدام الذكاء الاصطناعي وضوابط الذكاء التوليدي لبلدية تايبيه',
      description: 'تحليل شامل للدليل الإرشادي الصادر عن بلدية تايبيه لاستخدام الذكاء التوليدي، ويغطي أمن المعلومات، وحماية الخصوصية، والملكية الفكرية، وحدود المسؤولية الإدارية.',
      tags: ['إرشادات الذكاء', 'الذكاء التوليدي', 'الأمن السيبراني', 'الخصوصية', 'المسؤولية الإدارية'],
      sampleQuestions: [
        'ما هي القواعد والمحظورات الأساسية للموظفين الحكوميين وفق دليل العمل بالذكاء الاصطناعي؟',
        'كيف يحدد الدليل الإشراف البشري الإلزامي (Human-in-the-loop) في صياغة الخطابات والردود الرسمية؟',
        'كيف تمنع بلدية تايبيه تسريب البيانات السرية وبيانات المواطنين إلى النماذج السحابية الخارجية؟'
      ],
      keyCruxes: [
        {
          title: 'حماية أمن وسرية المعلومات مقابل رفع الكفاءة الإدارية',
          description: 'التوفيق بين الحظر الصارم لرفع البيانات الحساسة على السحابة التجارية ورغبة الموظفين في استغلال النماذج المتقدمة لتسريع المهام.',
          proPoints: [
            'الضوابط الصارمة تحمي السجلات السرية والبيانات الشخصية للمواطنين من التسريب',
            'إنشاء قنوات حكومية سحابية خاصة أو محلية يضمن بيئة عمل آمنة وموثوقة'
          ],
          conPoints: [
            'المبالغة في الحظر قد تدفع الموظفين للجوء إلى "الذكاء الخفي" عبر حساباتهم الشخصية غير المراقبة',
            'الاستضافة المحلية عالية التكلفة وتتأخر في التحديث مقارنة بالنماذج التجارية الرائدة'
          ]
        },
        {
          title: 'الذكاء الاصطناعي كمساعد مقابل المسؤولية القانونية والإدارية للموظف',
          description: 'التأكيد على أن الذكاء الاصطناعي أداة مساعدة فقط، مع احتفاظ الموظف بالمسؤولية الكاملة عن دقة القرارات والخطابات الرسمية.',
          proPoints: [
            'الالتزام بمبدأ المراجعة البشرية يمنع العشوائية الخوارزمية والتنصل من المسؤولية',
            'صيانة الشرعية الإدارية وثقة الجمهور في مخرجات الجهات الحكومية'
          ],
          conPoints: [
            'الثقة المفرطة في مخرجات الذكاء الاصطناعي دون تدقيق قد تؤدي إلى أخطاء قانونية وتعويضات',
            'الحاجة إلى تدريب مستمر لموظفي الدولة على فحص وتدقيق المخرجات'
          ]
        }
      ]
    }
  },

  'taipei-bureau-interviews': {
    zh: {
      category: '局處實務與首長訪談',
      title: '局處 AI 實務推動與首長訪談洞察',
      description: '彙整資訊局局長、人事處、觀傳局、都更處、自來水事業處等局處首長與主管之一線訪談，剖析推動歷程與挑戰。',
      tags: ['資訊局', '人事處', '觀傳局', '都更處', '自來水處', '首長訪談'],
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
    en: {
      category: 'Bureau Practices & Leadership Insights',
      title: 'Departmental AI Implementation & Leadership Interview Insights',
      description: 'Synthesis of executive interviews across DOIT (Department of Information Technology), Personnel Department, Department of Information and Tourism (TPEDOIT), Urban Renewal Office, and Taipei Water Department.',
      tags: ['DOIT', 'Personnel Dept', 'Tourism Dept', 'Urban Renewal', 'Water Dept', 'Executive Interviews'],
      sampleQuestions: [
        'What strategic vision did the DOIT Commissioner outline for AI infrastructure and governance in Taipei?',
        'What challenges and roadmaps did the Personnel Department share regarding citywide employee AI upskilling?',
        'What real-world considerations did the Tourism Department highlight regarding AI travel concierges?'
      ],
      keyCruxes: [
        {
          title: 'Centralized DOIT IT Management vs. Departmental Procurement Autonomy',
          description: 'Debating whether AI infrastructure, computing clusters, and APIs should be strictly centralized by DOIT or procured independently by functional bureaus.',
          proPoints: [
            'Centralized architecture prevents duplicative capital expenditure, enforces uniform security standards, and maximizes data synergy',
            'Facilitates a unified cross-departmental RAG knowledge platform and shared foundation models'
          ],
          conPoints: [
            'DOIT engineering bandwidth is constrained and may bottleneck urgent, specialized departmental needs',
            'Functional bureaus know their domain pain points best and can move faster with specialized commercial vendors'
          ]
        },
        {
          title: 'Organizational Culture & Bridging the AI Literacy Divide',
          description: 'Overcoming staff inertia, fear of punitive administrative errors, and measuring the real impact of Personnel Department training seminars.',
          proPoints: [
            'Systematic training tracks and innovation hackathons alleviate anxieties about workforce displacement',
            'Clear standard operating procedures (SOPs) lower psychological hesitation when using AI assistants'
          ],
          conPoints: [
            'Significant digital divide among senior personnel results in steep learning curves',
            'Lack of direct career incentive mechanisms to reward grassroots public innovation'
          ]
        }
      ]
    },
    ja: {
      category: '局所実務・幹部インタビュー',
      title: '各部局における AI 推進実務と首長・幹部インタビューの洞察',
      description: '情報局長、人事所、観光伝播局、都市更新所、水道事業所などの局長・幹部への現場インタビューを総括し、推進の経緯と課題を解明。',
      tags: ['情報局', '人事所', '観光局', '都市更新所', '水道所', '幹部インタビュー'],
      sampleQuestions: [
        '情報局長はインタビューで市全体のAI基盤整備とガバナンスについてどのような戦略を述べましたか？',
        '人事所は公務員のAI活用能力向上や研修においてどのような課題と計画を示しましたか？',
        '観光伝播局はスマート観光やプロモーションへのAI適用でどのような実践的知見を得ましたか？'
      ],
      keyCruxes: [
        {
          title: '情報局による一元管理 vs. 各業務局の独自調達・開発',
          description: '全庁的なAIインフラやAPI基盤を情報局が一括統括すべきか、各局の個別業務に合わせて自主発注を認めるべきかの議論。',
          proPoints: [
            '統合プラットフォームにより重複投資を回避し、セキュリティ基準の統一と全庁データの相乗効果を実現',
            '全庁共通のRAG知識ベースや基盤モデルの共有を推進しやすい'
          ],
          conPoints: [
            '情報局のリソースに限界があり、各局の緊急で高度に特化したニーズへの即応が困難になるリスク',
            '業務主管局の方が課題を深く理解しており、業界の専門ソリューションと迅速に連携できる'
          ]
        },
        {
          title: '行政組織の文化変革と AI リテラシーの格差克服',
          description: '新技術への抵抗感や失敗時の処分への懸念を解消し、人事所によるAI研修を現場の実践力に定着させる課題。',
          proPoints: [
            '体系的な研修と実践コンテストにより、AIによる人員削減への不安を段階的に払拭',
            '明確な業務SOPを整備することで、職員の心理的ハードルを低減'
          ],
          conPoints: [
            'ベテラン職員を中心とするデジタルデバイドが存在し、習熟に時間を要する',
            '現場の公務員が業務革新に自発的に取り組むための評価・インセンティブ制度の不足'
          ]
        }
      ]
    },
    fr: {
      category: 'Pratiques des services & Entretiens de direction',
      title: 'Mise en œuvre sectorielle de l’IA & Perspectives des dirigeants',
      description: 'Synthèse des entretiens avec les directions clés : Informatique (DOIT), Ressources humaines, Tourisme, Rénovation urbaine et Eaux de Taipei.',
      tags: ['DOIT Informatique', 'Ressources humaines', 'Tourisme', 'Rénovation', 'Eaux', 'Entretiens dirigeants'],
      sampleQuestions: [
        'Quelle vision stratégique le directeur du DOIT a-t-il partagée pour l’infrastructure IA de Taipei ?',
        'Quels défis la direction des RH a-t-elle identifiés dans la montée en compétences des agents ?',
        'Quels enseignements la direction du Tourisme a-t-elle tirés des assistants de voyage intelligents ?'
      ],
      keyCruxes: [
        {
          title: 'Centralisation par la direction informatique (DOIT) vs. autonomie d’achat des services',
          description: 'Faut-il centraliser les modèles, GPU et APIs au sein du DOIT ou permettre à chaque direction de contracter des solutions spécialisées.',
          proPoints: [
            'Évite les doublons budgétaires, harmonise la sécurité et valorise les synergies de données',
            'Favorise une base de connaissances RAG unifiée pour l’ensemble de la municipalité'
          ],
          conPoints: [
            'Goulot d’étranglement technique au DOIT face aux demandes urgentes des directions métiers',
            'Les services connaissent mieux leurs besoins opérationnels et peuvent agir plus rapidement avec le secteur privé'
          ]
        },
        {
          title: 'Transformation culturelle et maîtrise des compétences IA',
          description: 'Surmonter la peur du changement ou de la sanction administrative et valoriser les formations RH.',
          proPoints: [
            'Formations continues et défis d’innovation réduisant la crainte du remplacement technologique',
            'Les procédures opérationnelles standardisées sécurisent l’usage quotidien des agents'
          ],
          conPoints: [
            'Fracture numérique persistante chez une partie des agents seniors',
            'Manque de mécanismes de valorisation pour récompenser les initiatives d’innovation de terrain'
          ]
        }
      ]
    },
    es: {
      category: 'Prácticas de departamentos y entrevistas a directivos',
      title: 'Implementación departamental de IA y perspectivas de liderazgo',
      description: 'Síntesis de entrevistas a directores y jefes de servicio del Departamento de Tecnología de la Información (DOIT), Recursos Humanos, Turismo, Renovación Urbana y Aguas de Taipéi.',
      tags: ['DOIT Tecnología', 'Recursos Humanos', 'Turismo', 'Renovación Urbana', 'Aguas', 'Entrevistas'],
      sampleQuestions: [
        '¿Cuál es la estrategia del director de DOIT para la infraestructura y gobernanza de IA en Taipéi?',
        '¿Qué retos y planes expuso el departamento de personal sobre la capacitación de los funcionarios en IA?',
        '¿Qué aprendizajes prácticos compartió el departamento de turismo sobre guías turísticas inteligentes?'
      ],
      keyCruxes: [
        {
          title: 'Gestión centralizada por el DOIT vs. compras autónomas de cada concejalía',
          description: 'Debate sobre si centralizar servidores, APIs y modelos en el departamento informático (DOIT) o permitir licitaciones independientes por área.',
          proPoints: [
            'La plataforma central evita duplicidades presupuestarias y asegura estándares de ciberseguridad homogéneos',
            'Facilita la creación de un repositorio de conocimiento RAG compartido para toda la ciudad'
          ],
          conPoints: [
            'El equipo técnico de DOIT tiene recursos limitados y puede retrasar proyectos departamentales urgentes',
            'Las concejalías conocen mejor sus necesidades específicas y conectan más rápido con soluciones de mercado'
          ]
        },
        {
          title: 'Cultura interna municipal y superación de la brecha de alfabetización en IA',
          description: 'Vencer la resistencia al cambio tecnológico, el temor a sanciones y consolidar los programas de formación.',
          proPoints: [
            'Formación sistemática y concursos de casos prácticos que reducen la ansiedad por el reemplazo laboral',
            'Protocolos de trabajo estandarizados (SOP) que reducen la inseguridad al usar herramientas de IA'
          ],
          conPoints: [
            'Brecha digital acusada entre el personal veterano con curvas de aprendizaje más lentas',
            'Falta de incentivos profesionales directos para premiar a los funcionarios que innovan en procesos'
          ]
        }
      ]
    },
    ru: {
      category: 'Практика ведомств и интервью с руководителями',
      title: 'Практика внедрения ИИ в департаментах и экспертные интервью',
      description: 'Обобщение интервью с главами департамента информационных технологий (DOIT), управления кадров, департамента туризма, градостроительства и водоснабжения Тайбэя.',
      tags: ['DOIT', 'Управление кадров', 'Туризм', 'Градостроительство', 'Водоканал', 'Интервью'],
      sampleQuestions: [
        'Какую стратегию развития инфраструктуры ИИ озвучил глава департамента информационных технологий?',
        'С какими вызовами столкнулось управление кадров при обучении госслужащих работе с ИИ?',
        'Какой практический опыт внедрения ИИ в туристические сервисы выделил департамент туризма?'
      ],
      keyCruxes: [
        {
          title: 'Централизованное управление DOIT vs. автономия закупок ведомств',
          description: 'Должна ли инфраструктура и вычислительные мощности ИИ централизованно администрироваться DOIT или закупаться каждым ведомством отдельно.',
          proPoints: [
            'Единая платформа исключает дублирование расходов, гарантирует единые стандарты ИБ и синергию данных',
            'Способствует созданию общегородской базы знаний RAG и совместных базовых моделей'
          ],
          conPoints: [
            'Ресурсы DOIT ограничены, что создает задержки для срочных специализированных запросов ведомств',
            'Отраслевые департаменты лучше понимают свои задачи и быстрее находят коммерческие решения'
          ]
        },
        {
          title: 'Культура госслужбы и преодоление дефицита компетенций в сфере ИИ',
          description: 'Преодоление страха перед технологиями и наказанием за ошибки, а также оценка отдачи от обучающих программ.',
          proPoints: [
            'Системные тренинги и конкурсы снижают тревогу сотрудников по поводу замещения труда технологиями',
            'Типовые регламенты (SOP) снижают барьер начала использования ИИ в повседневной работе'
          ],
          conPoints: [
            'Заметный цифровой разрыв у возрастных сотрудников и более длительное обучение',
            'Недостаток мотивационных механизмов для поощрения низовой инновационной активности'
          ]
        }
      ]
    },
    ar: {
      category: 'ممارسات الإدارات ومقابلات القيادات',
      title: 'تطبيق الذكاء الاصطناعي في الإدارات ورؤى مقابلات المسؤولين',
      description: 'خلاصة مقابلات مديري إدارة تكنولوجيا المعلومات (DOIT)، وإدارة الموارد البشرية، والسياحة، والتطوير العمراني، وهيئة مياه تايبيه حول مسيرة وتحديات التطبيق.',
      tags: ['إدارة تكنولوجيا المعلومات', 'الموارد البشرية', 'السياحة', 'التطوير العمراني', 'هيئة المياه', 'مقابلات'],
      sampleQuestions: [
        'ما هي الرؤية الاستراتيجية التي طرحها مدير إدارة التكنولوجيا لحوكمة وبنية الذكاء الاصطناعي؟',
        'ما هي التحديات التي واجهتها إدارة الموارد البشرية في تدريب وتمكين موظفي الحكومة؟',
        'ما هي التجارب والاعتبارات العملية التي أوضحتها إدارة السياحة عند استخدام المساعدات الذكية؟'
      ],
      keyCruxes: [
        {
          title: 'الإدارة المركزية الموحدة لتقنية المعلومات مقابل الاستقلالية الشرائية للإدارات',
          description: 'هل يجب أن تتولى إدارة تكنولوجيا المعلومات (DOIT) البنية التحتية والنماذج مركزياً، أم يُسمح لكل قطاع بالتعاقد المستقل.',
          proPoints: [
            'المنصة الموحدة تمنع الهدر المالي، وتضمن معايير أمنية متسقة وتكاملاً لبيانات المدينة',
            'تسهيل بناء قاعدة معرفة RAG مشتركة ونماذج أساسية موحدة لجميع القطاعات'
          ],
          conPoints: [
            'محدودية كوادر إدارة التقنية قد تعطل الاستجابة السريعة لمتطلبات الإدارات التخصصية العاجلة',
            'الإدارات التنفيذية أدرى باحتياجاتها التشغيلية وقادرة على الاتفاق السريع مع الشركات المتخصصة'
          ]
        },
        {
          title: 'الثقافة المؤسسية وسد الفجوة المعرفية في مهارات الذكاء الاصطناعي',
          description: 'مواجهة مقاومة التغيير والخوف من العقوبات الإدارية، وتعزيز جدوى البرامج التدريبية.',
          proPoints: [
            'التدريب المنهجي ومسابقات الابتكار تبدد مخاوف الموظفين من الاستغناء عنهم لصالح الآلة',
            'إعداد إجراءات عمل قياسية (SOP) يزيل التردد النفسي لدى الموظفين'
          ],
          conPoints: [
            'فجوة رقمية واضحة لدى الموظفين ذوي الخبرة الطويلة تتطلب وقتاً أطول للتعلم',
            'غياب الحوافز الوظيفية المباشرة لتشجيع الموظفين على ابتكار وتطوير أساليب العمل'
          ]
        }
      ]
    }
  },

  'taipei-tpmo-smartcity': {
    zh: {
      category: '概念驗證與公私協力',
      title: 'TPMO 台北智慧城市專案辦公室與概念驗證 (PoC)',
      description: '探討台北智慧城市專案辦公室 (TPMO) 採行之「1+7 智慧領域」架構、民間提案 PoC 試辦機制以及國際智慧城市評比經驗。',
      tags: ['TPMO', '智慧城市', 'PoC試辦', '公私協力', '1+7領域', '城市治理'],
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
    },
    en: {
      category: 'Proof of Concept & Public-Private Partnerships',
      title: 'TPMO Taipei Smart City Project Office & Proof of Concept (PoC)',
      description: 'Exploring the "1+7 Smart Domains" framework of the Taipei Smart City Project Office (TPMO), bottom-up private sector PoC sandbox mechanisms, and global smart city rankings.',
      tags: ['TPMO', 'Smart City', 'PoC Sandbox', 'PPP', '1+7 Domains', 'Urban Governance'],
      sampleQuestions: [
        'What role does TPMO play in Taipei’s smart city framework and how does the "1+7 domains" model work?',
        'How can private companies participate in smart city and AI Proof-of-Concept (PoC) trials through TPMO?',
        'What are Taipei’s key strengths and improvement areas in international smart city indices?'
      ],
      keyCruxes: [
        {
          title: 'Crossing the "Valley of Death": Bridging PoC Trials to Mainstream Public Procurement',
          description: 'Navigating the gap between successful TPMO PoC trials and institutional government procurement constrained by the Government Procurement Act and annual budgeting cycles.',
          proPoints: [
            'The city provides real-world testbeds for zero-barrier corporate trial and error, spurring tech innovation',
            'Enables city officials to empirically validate efficacy before committing large-scale taxpayer budgets'
          ],
          conPoints: [
            'Under government procurement laws, PoC vendors cannot be awarded sole-source contracts and must re-compete publicly',
            'Lack of multi-year operational budgets often leaves successful pilots stranded as one-off showcases'
          ]
        }
      ]
    },
    ja: {
      category: '実証実験・官民共創',
      title: 'TPMO 台北スマートシティ推進室と概念実証 (PoC)',
      description: '台北スマートシティプロジェクトオフィス（TPMO）が推進する「1+7スマート領域」フレームワーク、民間提案型PoC実証実験、および国際スマートシティ評価の取り組みを検証。',
      tags: ['TPMO', 'スマートシティ', 'PoC実証', '官民連携', '1+7領域', '都市ガバナンス'],
      sampleQuestions: [
        'TPMOは台北スマートシティ構想においてどのような役割を担い、「1+7領域」はどのように機能していますか？',
        '民間企業はTPMOを通じてどのようにスマートシティやAIの概念実証（PoC）に参加できますか？',
        '世界のスマートシティランキングにおける台北市の強みと今後の改善点は何ですか？'
      ],
      keyCruxes: [
        {
          title: 'PoC実証実験から本格調達への「死の谷（Valley of Death）」克服',
          description: 'TPMOを通じて成功したAI実証実験が、各局の正式な予算化や政府調達手続きに移行する際の制度的障壁。',
          proPoints: [
            '行政が実証フィールドを提供し、企業が低リスクで迅速に試行錯誤できる環境を整備',
            '効果を事前検証してから本格導入を判断できるため、税金投入のリスクを抑制'
          ],
          conPoints: [
            '調達法の規制により、PoCを実施した企業であっても一般入札を経る必要があり、直接随意契約ができない',
            '各局に長期的な運用保守予算が確保されていない場合、優れた実証案件が一過性の展示で終わる恐れ'
          ]
        }
      ]
    },
    fr: {
      category: 'Preuve de concept & Partenariats public-privé',
      title: 'Bureau de projet Smart City TPMO & Preuve de concept (PoC)',
      description: 'Étude du cadre « 1+7 domaines intelligents » du TPMO de Taipei, des expérimentations PoC avec le secteur privé et des classements mondiaux des villes intelligentes.',
      tags: ['TPMO', 'Smart City', 'Expérimentation PoC', 'PPP', '1+7 Domaines', 'Gouvernance urbaine'],
      sampleQuestions: [
        'Quel est le rôle du TPMO et comment s’articule le modèle des « 1+7 domaines » ?',
        'Comment les entreprises peuvent-elles tester des solutions d’IA en conditions réelles via le TPMO ?',
        'Quels sont les atouts majeurs de Taipei dans les palmarès internationaux de smart cities ?'
      ],
      keyCruxes: [
        {
          title: 'Franchir la « Vallée de la mort » : du test PoC à la commande publique pérenne',
          description: 'Difficulté de convertir les projets pilotes réussis en contrats pérennes face aux contraintes du code des marchés publics.',
          proPoints: [
            'Offre un terrain d’expérimentation grandeur nature sans coût d’entrée pour stimuler l’innovation',
            'Permet à la mairie de valider l’utilité réelle avant d’engager des budgets significatifs'
          ],
          conPoints: [
            'Le droit de la commande publique impose une remise en concurrence sans garantie pour le porteur du PoC',
            'Le manque de budgets pluriannuels de maintenance risque de réduire les tests à des démonstrateurs éphémères'
          ]
        }
      ]
    },
    es: {
      category: 'Prueba de concepto y colaboración público-privada',
      title: 'Oficina del Proyecto Smart City (TPMO) y Pruebas de Concepto (PoC)',
      description: 'Estudio de la metodología de "1+7 Áreas Inteligentes" de la oficina TPMO de Taipéi, mecanismos de PoC con el sector privado y posicionamiento en rankings internacionales.',
      tags: ['TPMO', 'Ciudad Inteligente', 'PoC', 'Colaboración Público-Privada', '1+7 Áreas', 'Gobernanza Urbana'],
      sampleQuestions: [
        '¿Qué función cumple la oficina TPMO y cómo opera el marco de "1+7 áreas inteligentes"?',
        '¿Cómo pueden las empresas privadas presentar pruebas de concepto (PoC) de IA a través de TPMO?',
        '¿Cuáles son los puntos fuertes de Taipéi en los índices internacionales de Smart Cities?'
      ],
      keyCruxes: [
        {
          title: 'El "Valle de la Muerte": de la prueba de concepto a la licitación pública definitiva',
          description: 'La brecha existente entre un proyecto piloto de IA validado por TPMO y su conversión en una compra pública reglada bajo la ley de contratación.',
          proPoints: [
            'El ayuntamiento ofrece espacios reales de prueba que reducen el coste y riesgo de innovación para las empresas',
            'Permite comprobar la eficacia técnica antes de comprometer grandes inversiones presupuestarias'
          ],
          conPoints: [
            'La ley de contratación pública obliga a convocar licitación abierta, impidiendo adjudicaciones directas a quien hizo la PoC',
            'La ausencia de partidas de mantenimiento plurianual puede dejar pilotos exitosos sin continuidad'
          ]
        }
      ]
    },
    ru: {
      category: 'Пилотные проекты и государственно-частное партнерство',
      title: 'Офис проекта «Умный город» (TPMO) и пилотные внедрения (PoC)',
      description: 'Изучение структуры «1+7 умных сфер» проектного офиса TPMO Тайбэя, механизмов тестирования инициатив бизнеса (PoC) и позиций в мировых рейтингах.',
      tags: ['TPMO', 'Умный город', 'Тестирование PoC', 'ГЧП', '1+7 сфер', 'Городское управление'],
      sampleQuestions: [
        'Какую роль играет TPMO в цифровизации Тайбэя и как устроена концепция «1+7 сфер»?',
        'Как коммерческие компании могут протестировать свои ИИ-решения через платформу TPMO?',
        'В чем конкурентные преимущества Тайбэя в мировых рейтингах Smart City?'
      ],
      keyCruxes: [
        {
          title: '«Долина смерти»: переход от успешного пилота (PoC) к регулярным госзакупкам',
          description: 'Сложности масштабирования успешных пилотных проектов ИИ из-за жестких ограничений закона о госзакупках и бюджетных циклов.',
          proPoints: [
            'Предоставление городских площадок для бесплатного тестирования технологий стимулирует рынок инноваций',
            'Позволяет муниципалитету проверить реальную пользу до выделения масштабных бюджетных средств'
          ],
          conPoints: [
            'Законодательство о госзакупках требует проведения открытого конкурса без преференций разработчику PoC',
            'Отсутствие бюджета на долгосрочное сопровождение превращает удачные пилоты в разовые презентации'
          ]
        }
      ]
    },
    ar: {
      category: 'إثبات المفهوم والشراكة بين القطاعين العام والخاص',
      title: 'مكتب مشاريع المدينة الذكية في تايبيه (TPMO) ومشاريع إثبات المفهوم (PoC)',
      description: 'استكشاف هيكل "1+7 مجالات ذكية" لمكتب TPMO، وآليات اختبار المقترحات المبتكرة للشركات الخاصة، وتجارب التصنيفات الدولية للمدن الذكية.',
      tags: ['مكتب TPMO', 'المدينة الذكية', 'إثبات المفهوم PoC', 'الشراكة بين القطاعين', '1+7 مجالات', 'حوكمة المدن'],
      sampleQuestions: [
        'ما هو دور مكتب TPMO وكيف يعمل نموذج "1+7 مجالات ذكية"؟',
        'كيف يمكن لشركات القطاع الخاص المشاركة في تجارب إثبات المفهوم (PoC) لتطبيقات الذكاء الاصطناعي؟',
        'ما هي نقاط القوة والفرص لتايبيه في المؤشرات العالمية للمدن الذكية؟'
      ],
      keyCruxes: [
        {
          title: 'تجاوز "وادي الموت": الانتقال من تجربة إثبات المفهوم إلى الشراء الحكومي الرسمي',
          description: 'التحديات التي تواجه المشاريع التجريبية الناجحة عند تحويلها إلى مناقصات حكومية رسمية وفق قانون المشتريات والموازنات السنوية.',
          proPoints: [
            'توفير بيئات وتطبيقات واقعية للشركات لاختبار الابتكارات بأقل تكلفة وتحفيز الصناعة',
            'تمكين البلدية من قياس الأثر والجدوى قبل اتخاذ قرارات الشراء الواسعة النطاق'
          ],
          conPoints: [
            'يلزم قانون المشتريات بطرح مناقصة عامة مما يمنع الترسية المباشرة على الشركة المطورة للتجربة',
            'عدم توفر موازنات تشغيل طويلة الأجل لدى الإدارات قد يحول المشاريع المميزة إلى عروض مؤقتة فقط'
          ]
        }
      ]
    }
  }
};

export const INITIAL_TOPICS: Topic[] = [
  {
    id: 'taipei-1999-ai',
    category: '市民服務與智慧客服',
    title: '1999 市民當家熱線導入 AI 效益與評估',
    description: '深入剖析台北市 1999 市民熱線導入語音辨識、意圖分類與 AI 客服之效益研究，以及研考會話務管理組在第一線的實務考量與限制。',
    tags: ['1999市民熱線', '研考會', 'AI語音客服', '智慧派工', '情緒辨識', '效益評估'],
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
          '針對路燈不亮、垃圾清運等標準化題型，AI 可 24 小時自動派工分流，顯著降低話務負載',
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
    tags: ['AI作業指引', '生成式AI', '資安防護', '個資隱私', '行政責任', '公文輔助'],
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
    tags: ['資訊局', '人事處', '觀傳局', '都更處', '自來水處', '首長訪談'],
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
    tags: ['TPMO', '智慧城市', 'PoC試辦', '公私協力', '1+7領域', '城市治理'],
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

/**
 * Merges localized strings from TOPIC_TRANSLATIONS over a raw Topic
 */
export function getLocalizedTopic(rawTopic: Topic, lang: LanguageCode): Topic {
  const trans = TOPIC_TRANSLATIONS[rawTopic.id]?.[lang];
  if (!trans) return rawTopic;
  return {
    ...rawTopic,
    category: trans.category || rawTopic.category,
    title: trans.title || rawTopic.title,
    description: trans.description || rawTopic.description,
    tags: trans.tags || rawTopic.tags,
    sampleQuestions: trans.sampleQuestions || rawTopic.sampleQuestions,
    keyCruxes: trans.keyCruxes || rawTopic.keyCruxes,
  };
}
