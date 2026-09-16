import {InterfaceLanguage} from './languages';
const keys=['city','allCities','sources','allSources','chart','report','slides','library','tasks','logout'] as const;
const values:Record<InterfaceLanguage,string[]>={
  zh:['研究城市（選填）','不限城市','來源語言（可多選）','所有來源語言','製作圖表','製作報告 PDF','產出投影片','文件庫','我的產出','登出'],
  en:['City (optional)','All cities','Source languages','All source languages','Create chart','Create PDF report','Create slides','Library','My tasks','Sign out'],
  ja:['都市（任意）','すべての都市','原文の言語','すべての原文言語','図表を作成','PDF レポート','スライドを作成','資料一覧','作成タスク','ログアウト'],
  fr:['Ville (facultatif)','Toutes les villes','Langues des sources','Toutes les langues','Créer un graphique','Rapport PDF','Créer des diapositives','Documents','Mes tâches','Déconnexion'],
  es:['Ciudad (opcional)','Todas las ciudades','Idiomas de fuentes','Todos los idiomas','Crear gráfico','Informe PDF','Crear diapositivas','Documentos','Mis tareas','Cerrar sesión'],
  ru:['Город (необязательно)','Все города','Языки источников','Все языки','Создать диаграмму','Отчёт PDF','Создать слайды','Документы','Мои задачи','Выйти'],
};
export function workspaceLabels(language:InterfaceLanguage) {
  return Object.fromEntries(keys.map((key,index)=>[key,values[language][index]])) as Record<typeof keys[number],string>;
}
