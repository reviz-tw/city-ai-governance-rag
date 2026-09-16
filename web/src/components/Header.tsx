import {Menu} from 'lucide-react';
import {InterfaceLanguage, INTERFACE_LANGUAGES, normalizeInterfaceLanguage} from '../lib/languages';
import {UIStrings} from '../i18n';
import {researchCopy} from '../lib/research-copy';
import {workspaceLabels} from '../lib/workspace-labels';

export function Header({t, lang, onLangChange, email, loading, onLogout, onOpenScope}: {
  t: UIStrings; lang: InterfaceLanguage; onLangChange: (lang: InterfaceLanguage) => void;
  email: string; loading: boolean; onLogout: () => void; onOpenScope: () => void;
}) {
  const c = researchCopy(lang);
  return <header className="app-header">
    <button className="btn btn-icon scope-toggle" onClick={onOpenScope} aria-label={c.scopeToggle}><Menu size={20}/></button>
    <div className="brand"><span className="brand-dot"/><span className="brand-name">{t.brand}</span><span className="brand-subtitle">{t.brandSub}</span></div>
    <div className="header-controls">
      <span className={`availability ${loading ? 'is-busy' : ''}`} role="status"><span/>{loading ? t.searchingText : t.liveTag}</span>
      <select className="input interface-language" value={lang} onChange={e => onLangChange(normalizeInterfaceLanguage(e.target.value))} aria-label={c.languageLabel}>{Object.entries(INTERFACE_LANGUAGES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select>
      <span className="account-email" title={email}>{email}</span>
      <button className="btn btn-secondary logout-button" onClick={onLogout}>{workspaceLabels(lang).logout}</button>
    </div>
  </header>;
}
