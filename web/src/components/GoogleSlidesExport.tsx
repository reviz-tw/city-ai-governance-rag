import {useEffect, useState} from 'react';
import {api} from '../lib/api';
import {loadGoogleIdentity} from '../lib/google-identity';
import {authorizeDrive, exportGoogleSlides, GoogleSlidesError, PPTX_MIME} from '../lib/google-slides';
import {useLocale} from '../lib/locale';
import type {PanelKey} from '../lib/panel-copy';

export function GoogleSlidesExport({job}: {job:any}) {
  const {t} = useLocale();
  const [config, setConfig] = useState<{clientId:string; email:string} | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<PanelKey | null>(null);
  const [link, setLink] = useState('');
  const [attempt, setAttempt] = useState(0);
  const file = job.result.files.find((item:any) => item.mime === PPTX_MIME);
  useEffect(() => {
    let active = true;
    setError(null);
    Promise.all([loadGoogleIdentity(), api('/api/auth/config'), api('/api/auth/me')]).then(([,auth,user]) => {
      if (!auth.client_id || !user.email) throw new Error('Missing Google configuration');
      if (active) setConfig({clientId:auth.client_id,email:user.email});
    }).catch(() => {if (active) setError('slidesUnavailable');});
    return () => {active = false;};
  }, [attempt]);
  if (!file) return null;
  const create = () => {
    if (!config || busy) return;
    setBusy(true); setError(null);
    // Start the popup synchronously in the click handler to preserve user activation.
    authorizeDrive(window.google, config.clientId, config.email)
      .then(token => exportGoogleSlides({id:job.id,revision:job.revision,title:job.draft?.title,fileName:file.name}, token, config.email, location.origin))
      .then(setLink)
      .catch(err => setError(err instanceof GoogleSlidesError ? err.key : 'slidesFailed'))
      .finally(() => setBusy(false));
  };
  return <section className="google-slides-export">
    <h3>Google Slides</h3>
    <p>{t('slidesIntro')}</p>
    {link ? <a className="btn btn-primary" href={link} target="_blank" rel="noopener noreferrer">{t('slidesOpen')}</a> :
      <button className="btn btn-primary" disabled={!config || busy || job.stale} onClick={create}>{t(busy ? 'slidesCreating' : 'slidesCreate')}</button>}
    {!config && !error && <p role="status">{t('loading')}</p>}
    {error && <p role="alert">{t(error)}</p>}
    {!config && error && <button className="btn" onClick={() => setAttempt(value => value+1)}>{t('retry')}</button>}
    {link && <p role="status">{t('slidesSaved')}</p>}
    <p><small>{t('slidesDownloads')}</small></p>
  </section>;
}
