import { InterfaceLanguage } from './lib/languages';

export interface UIStrings {
  brand: string;
  brandSub: string;
  liveTag: string;
  welcomeTitle: string;
  welcomeDesc: string;
  sampleQuestions: string[];
  inputPlaceholder: string;
  multilingualNote: string;
  restartBtn: string;
  copyBtn: string;
  copiedBtn: string;
  sourcesHeader: string;
  searchingText: string;
  sourceCitationBadge: string;
  clearHistoryTitle: string;
  drawerCloseLabel: string;
  sendAriaLabel: string;
}

export const STRINGS: Record<InterfaceLanguage, UIStrings> = {
  zh: {
    brand: 'AI 治理政策顧問系統',
    brandSub: "以原始文獻研究城市 AI 政策",
    liveTag: '線上即時問答',
    welcomeTitle: 'AI 治理政策與訪談知識顧問',
    welcomeDesc: "您可研究任何城市的 AI 風險、公共治理與使用規範，並查閱原始來源。",
    sampleQuestions: ["如何建立城市 AI 風險評估流程？", "政府使用生成式 AI 有哪些治理原則？", "比較來源對透明度與隱私的建議。"],
    inputPlaceholder: '輸入你的問題……',
    multilingualNote: '支援中文、英文、日文、法文、西班牙文、俄文、韓文與德文提問',
    restartBtn: '重新開始',
    copyBtn: '複製回答',
    copiedBtn: '已複製',
    sourcesHeader: '檢索引用政策文獻',
    searchingText: '正在檢索 Vertex AI Search 並整合政策文獻...',
    sourceCitationBadge: '引用來源',
    clearHistoryTitle: '清除當前對話紀錄',
    drawerCloseLabel: '關閉抽屜',
    sendAriaLabel: '發送問題',
  },
  en: {
    brand: 'City AI Governance Advisor',
    brandSub: "Research city AI policy with original sources",
    liveTag: 'Live Q&A online',
    welcomeTitle: 'City AI Governance Knowledge Advisor',
    welcomeDesc: "Explore AI risks, public governance and usage policies across cities, with original sources.",
    sampleQuestions: ["How should cities assess AI risks?", "What principles govern public-sector generative AI?", "Compare the sources on transparency and privacy."],
    inputPlaceholder: 'Type your question…',
    multilingualNote: 'Supports questions in Chinese, English, Japanese, French, Spanish, Russian, Korean and German',
    restartBtn: 'Restart',
    copyBtn: 'Copy answer',
    copiedBtn: 'Copied',
    sourcesHeader: 'Cited policy documents',
    searchingText: 'Searching Vertex AI Search and synthesizing policy documents...',
    sourceCitationBadge: 'Citation Source',
    clearHistoryTitle: 'Clear current conversation history',
    drawerCloseLabel: 'Close drawer',
    sendAriaLabel: 'Send question',
  },
  ja: {
    brand: '都市 AI ガバナンス政策アドバイザー',
    brandSub: "原典に基づく都市 AI 政策の調査",
    liveTag: 'リアルタイムQ&A',
    welcomeTitle: '都市 AI ガバナンス知識アドバイザー',
    welcomeDesc: "都市の AI リスク、公共ガバナンス、利用指針を原典とともに調べられます。",
    sampleQuestions: ["都市は AI のリスクをどう評価すべきですか？", "行政の生成 AI 利用にはどのような原則がありますか？", "透明性とプライバシーに関する資料を比較してください。"],
    inputPlaceholder: '質問を入力してください……',
    multilingualNote: '中国語・英語・日本語・フランス語・スペイン語・ロシア語・韓国語・ドイツ語の質問に対応',
    restartBtn: 'やり直す',
    copyBtn: '回答をコピー',
    copiedBtn: 'コピー済み',
    sourcesHeader: '引用された政策文献',
    searchingText: 'Vertex AI Search を検索し政策文献を統合中...',
    sourceCitationBadge: '引用元',
    clearHistoryTitle: '現在の対話履歴を消去',
    drawerCloseLabel: 'ドロワーを閉じる',
    sendAriaLabel: '質問を送信',
  },
  fr: {
    brand: 'Conseiller en gouvernance de l’IA des villes',
    brandSub: "Étudier les politiques urbaines d’IA à partir des sources",
    liveTag: 'Q&R en direct',
    welcomeTitle: 'Conseiller de connaissances en gouvernance de l’IA des villes',
    welcomeDesc: "Explorez les risques, la gouvernance publique et les règles d’usage de l’IA dans différentes villes.",
    sampleQuestions: ["Comment les villes doivent-elles évaluer les risques de l’IA ?", "Quels principes encadrent l’IA générative dans le secteur public ?", "Comparez les sources sur la transparence et la vie privée."],
    inputPlaceholder: 'Saisissez votre question…',
    multilingualNote: 'Questions en chinois, anglais, japonais, français, espagnol, russe, coréen et allemand',
    restartBtn: 'Recommencer',
    copyBtn: 'Copier',
    copiedBtn: 'Copié',
    sourcesHeader: 'Documents de politique cités',
    searchingText: 'Recherche dans Vertex AI Search et synthèse en cours...',
    sourceCitationBadge: 'Source de citation',
    clearHistoryTitle: 'Effacer l’historique de conversation actuel',
    drawerCloseLabel: 'Fermer le tiroir',
    sendAriaLabel: 'Envoyer la question',
  },
  es: {
    brand: 'Asesor de gobernanza de IA de ciudades',
    brandSub: "Investigar políticas urbanas de IA con fuentes originales",
    liveTag: 'Preguntas y respuestas en vivo',
    welcomeTitle: 'Asesor de conocimiento en gobernanza de IA de ciudades',
    welcomeDesc: "Explore los riesgos, la gobernanza pública y las normas de uso de IA en distintas ciudades.",
    sampleQuestions: ["¿Cómo deben evaluar las ciudades los riesgos de la IA?", "¿Qué principios rigen la IA generativa en el sector público?", "Compare las fuentes sobre transparencia y privacidad."],
    inputPlaceholder: 'Escriba su pregunta…',
    multilingualNote: 'Preguntas en chino, inglés, japonés, francés, español, ruso, coreano y alemán',
    restartBtn: 'Reiniciar',
    copyBtn: 'Copiar',
    copiedBtn: 'Copiado',
    sourcesHeader: 'Documentos de política citados',
    searchingText: 'Buscando en Vertex AI Search y sintetizando documentos...',
    sourceCitationBadge: 'Fuente citada',
    clearHistoryTitle: 'Borrar historial de conversación actual',
    drawerCloseLabel: 'Cerrar panel',
    sendAriaLabel: 'Enviar pregunta',
  },
  ru: {
    brand: 'Советник по управлению ИИ городов',
    brandSub: "Исследование городской политики ИИ по первоисточникам",
    liveTag: 'Онлайн Q&A',
    welcomeTitle: 'Консультант по знаниям управления ИИ городов',
    welcomeDesc: "Изучайте риски ИИ, государственное управление и правила использования в разных городах.",
    sampleQuestions: ["Как городам оценивать риски ИИ?", "Какие принципы регулируют генеративный ИИ в госсекторе?", "Сравните источники о прозрачности и конфиденциальности."],
    inputPlaceholder: 'Введите ваш вопрос…',
    multilingualNote: 'Вопросы на китайском, английском, японском, французском, испанском, русском, корейском и немецком',
    restartBtn: 'Начать заново',
    copyBtn: 'Копировать',
    copiedBtn: 'Скопировано',
    sourcesHeader: 'Цитируемые документы',
    searchingText: 'Поиск в Vertex AI Search и анализ документов...',
    sourceCitationBadge: 'Источник цитаты',
    clearHistoryTitle: 'Очистить текущую историю переписки',
    drawerCloseLabel: 'Закрыть панель',
    sendAriaLabel: 'Отправить вопрос',
  },
};
