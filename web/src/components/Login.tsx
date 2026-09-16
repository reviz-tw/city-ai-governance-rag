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
        window.google.accounts.id.renderButton(root.current, {theme:'outline', size:'large', shape:'pill', text:'signin_with', width:Math.min(400, root.current?.clientWidth || 300)});
      } catch (e: any) {setError(e.message);}
    };
    script.onerror = () => setError('無法載入 Google 登入，請重新整理後重試。');
    document.head.appendChild(script);
    return () => {active = false; script.remove();};
  }, [onLogin]);
  return <main className="login-page"><div className="login-card">
    <p className="eyebrow">City AI governance</p>
    <h1>城市 AI 治理研究</h1>
    <p className="login-description">用你自己的話提問，回答會附上原始文件。<br/>登入後可閱讀原文、產出報告與投影片。</p>
    <div className="google-signin" ref={root}/>
    {error && <p role="alert">{error}</p>}
    <p className="login-note">只取得基本身分，不讀取你的信件或雲端檔案。</p>
  </div></main>;
}
