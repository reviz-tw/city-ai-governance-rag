import {CONTENT_LANGUAGES, InterfaceLanguage} from '../lib/languages';
import {researchCopy} from '../lib/research-copy';

export function ResearchSidebar({lang, city, sources, loading, canCreate, panel, onCity, onSources, onPanel}: {
  lang: InterfaceLanguage; city: string; sources: string[]; loading: boolean; canCreate: boolean; panel: string;
  onCity: (value: string) => void; onSources: (value: string[]) => void; onPanel: (value: string) => void;
}) {
  const c = researchCopy(lang);
  return <div className="research-sidebar-content">
    <section className="sidebar-section">
      <h2 className="eyebrow">{c.scope}</h2>
      <label className="field-label">{c.city}<input className="input" value={city} disabled={loading} onChange={e => onCity(e.target.value)} placeholder={c.cityPlaceholder}/></label>
      <p className="field-hint">{c.cityHint}</p>
      <fieldset className="source-languages"><legend>{c.languages}</legend>
        <div className="language-chips">
          <button className="language-chip" aria-pressed={!sources.length} onClick={() => onSources([])}>{c.allLanguages}</button>
          {Object.entries(CONTENT_LANGUAGES).map(([code, name]) => <button key={code} className="language-chip" aria-pressed={sources.includes(code)} onClick={() => onSources(sources.includes(code) ? sources.filter(v => v !== code) : [...sources, code])}>{name}</button>)}
        </div>
        <p className="field-hint">{c.languageHint}</p>
      </fieldset>
    </section>
    <section className="sidebar-section">
      <h2 className="eyebrow">{c.make}</h2>
      <div className="output-options">
        {([['chart', c.chart, c.chartHint], ['pdf', c.report, c.reportHint], ['pptx', c.slides, c.slidesHint]]).map(([kind, title, hint]) => <button key={kind} className="output-option" disabled={!canCreate} onClick={() => onPanel(kind)}><span>{title}</span><small>{hint}</small></button>)}
      </div>
      {!canCreate && <p className="field-hint">{c.makeHint}</p>}
    </section>
    <nav className="sidebar-links" aria-label={c.scopeToggle}>
      {([['library', c.library], ['tasks', c.tasks], ['mcp', c.mcp]]).map(([value, label]) => <button key={value} className="sidebar-link" aria-current={panel === value ? 'page' : undefined} onClick={() => onPanel(value)}>{label}</button>)}
    </nav>
  </div>;
}
