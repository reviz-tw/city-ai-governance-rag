import {createContext, ReactNode, useContext} from 'react';
import {InterfaceLanguage} from './languages';
import {PanelKey, PANEL_COPY, panelError, panelText} from './panel-copy';
const Locale=createContext<InterfaceLanguage>('zh');
export function LocaleProvider({lang,children}:{lang:InterfaceLanguage;children:ReactNode}) {return <Locale.Provider value={lang}>{children}</Locale.Provider>;}
export function useLocale() {
  const lang=useContext(Locale);
  const t=(key:PanelKey,params:Record<string,string|number>={})=>panelText(lang,key,params);
  return {lang,t,error:(e:unknown)=>t(panelError(e)),label:(value:string)=>value in PANEL_COPY?t(value as PanelKey):value,
    date:(timestamp:number)=>new Date(timestamp*1000).toLocaleString(lang==='zh'?'zh-TW':lang)};
}
