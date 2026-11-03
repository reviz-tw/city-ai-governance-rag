import {useEffect, useRef, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {loadGoogleIdentity} from '../lib/google-identity';
import {useLocale} from '../lib/locale';
import {InterfaceLanguage, INTERFACE_LANGUAGES, normalizeInterfaceLanguage} from '../lib/languages';
import {researchCopy} from '../lib/research-copy';
import {STRINGS} from '../i18n';
export function Login({onLogin, onLangChange}: {onLogin: (user: any) => void; onLangChange?: (lang: InterfaceLanguage) => void}) {
  const {lang,t,error:errorText} = useLocale();
  const root = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<unknown>(null);
  const [notConfigured, setNotConfigured] = useState(false);
  useEffect(() => {
    let active = true;
    setError(null);
    setNotConfigured(false);
    const initialize = async () => {
      try {
        await loadGoogleIdentity();
        const config = await api('/api/auth/config');
        if (!active) return;
        if (!config.client_id) {setNotConfigured(true); return;}
        window.google.accounts.id.initialize({client_id:config.client_id, callback: async ({credential}: {credential:string}) => {
          if (!active) return;
          try {const user=await api('/api/auth/login', jsonRequest({credential}));if(active)onLogin(user);} catch (e: any) {if(active)setError(e);}
        }});
        root.current?.replaceChildren();
        window.google.accounts.id.renderButton(root.current, {theme:'outline', size:'large', shape:'pill', text:'signin_with', locale:lang==='zh'?'zh-TW':lang, width:Math.min(400, root.current?.clientWidth || 300)});
      } catch (e: any) {if(active)setError(e);}
    };
    void initialize();
    return () => {active = false;};
  }, [onLogin,lang]);
  return <main className="login-page"><div className="login-card">
    {onLangChange && <select className="input interface-language" aria-label={researchCopy(lang).languageLabel} value={lang} onChange={e=>onLangChange(normalizeInterfaceLanguage(e.target.value))}>{Object.entries(INTERFACE_LANGUAGES).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select>}
    <p className="eyebrow">{STRINGS[lang].brandSub}</p>
    <h1>{STRINGS[lang].brand}</h1>
    <p className="login-description">{t('loginDescription')}</p>
    <div className="google-signin" ref={root}/>
    {notConfigured && <p role="alert">{t('loginNotConfigured')}</p>}
    {error != null && <p role="alert">{errorText(error)}</p>}
    <p className="login-note">{t('loginNote')}</p>
  </div></main>;
}
