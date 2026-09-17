declare global {interface Window {google?: any}}

let loading: Promise<void> | undefined;
// Sign-in and optional Drive authorization share one script, including on a restored session.
export function loadGoogleIdentity(): Promise<void> {
  if (window.google?.accounts?.oauth2 && window.google?.accounts?.id) return Promise.resolve();
  if (loading) return loading;
  loading = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    const timer = setTimeout(() => fail(), 20000);
    const fail = () => {
      clearTimeout(timer); script.remove(); loading = undefined;
      reject(new Error('Google Identity unavailable'));
    };
    script.onload = () => {clearTimeout(timer); resolve();};
    script.onerror = fail;
    document.head.appendChild(script);
  });
  return loading;
}
