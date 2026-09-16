import {useEffect, useRef, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
declare global {interface Window {google?: any}}
export function Login({onLogin}: {onLogin: (user: any) => void}) {
  const root = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client'; script.async = true;
    script.onload = async () => {
      try {
        const config = await api('/api/auth/config');
        if (!active) return;
        if (!config.client_id) {setError('Google 登入尚未設定，請由管理員設定 OAuth Client ID。'); return;}
        window.google.accounts.id.initialize({client_id:config.client_id, callback: async ({credential}: {credential:string}) => {
          try {onLogin(await api('/api/auth/login', jsonRequest({credential})));} catch (e: any) {setError(e.message);}
        }});
        window.google.accounts.id.renderButton(root.current, {theme:'outline', size:'large'});
      } catch (e: any) {setError(e.message);}
    };
    script.onerror = () => setError('無法載入 Google 登入，請重新整理後重試。');
    document.head.appendChild(script);
    return () => {active = false; script.remove();};
  }, [onLogin]);
  return <div className="login-card"><h1>城市 AI 治理研究</h1><p>使用 Google／Gmail 帳號登入，查閱來源、研究政策並製作報告。</p><div ref={root}/>{error && <p role="alert">{error}</p>}</div>;
}
