import {useLocale} from '../lib/locale';
import {InterfaceLanguage, INTERFACE_LANGUAGES, normalizeInterfaceLanguage} from '../lib/languages';
import {UIStrings} from '../i18n';
import {researchCopy} from '../lib/research-copy';
import {workspaceLabels} from '../lib/workspace-labels';

export function Header({t, lang, onLangChange, email, loading, onLogout, onPanel}: {
  t: UIStrings; lang: InterfaceLanguage; onLangChange: (lang: InterfaceLanguage) => void;
  email: string; loading: boolean; onLogout: () => void; onPanel: (panel:string) => void;
}) {
  const {t: text} = useLocale();
  const c = researchCopy(lang);
  return <header className="app-header">
    <div className="brand"><span className="brand-dot"/><span className="brand-name">{t.brand}</span><span className="brand-subtitle">{t.brandSub}</span></div>
    <div className="header-controls">
      <span className={`availability ${loading ? 'is-busy' : ''}`} role="status"><span/>{loading ? t.searchingText : t.liveTag}</span>
      <select className="input interface-language" value={lang} onChange={e => onLangChange(normalizeInterfaceLanguage(e.target.value))} aria-label={c.languageLabel}>{Object.entries(INTERFACE_LANGUAGES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select>
      <details className="header-tools"><summary className="btn btn-secondary">{text('tools')}</summary><nav><button className="btn" onClick={event=>{event.currentTarget.closest('details')?.removeAttribute('open');onPanel('tasks');}}>{text('tasks')}</button><button className="btn" onClick={event=>{event.currentTarget.closest('details')?.removeAttribute('open');onPanel('mcp');}}>{text('mcp')}</button></nav></details>
      <span className="account-email" title={email}>{email}</span>
      <button className="btn btn-secondary logout-button" onClick={onLogout}>{workspaceLabels(lang).logout}</button>
    </div>
  </header>;
}
