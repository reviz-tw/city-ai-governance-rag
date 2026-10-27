import {useLocale} from '../lib/locale';

export function ExtractionWarnings({warnings=[],audit=[]}:{warnings?:string[];audit?:any[]}) {
  const {t}=useLocale();
  if(!warnings.length&&!audit.some(p=>p.low_confidence||p.unassembled))return null;
  return <details className="extraction-warnings"><summary>{t('extractionWarnings')}</summary>
    {warnings.length>0&&<ul>{[...new Set(warnings)].map(w=><li key={w}>{w}</li>)}</ul>}
    {audit.filter(p=>p.low_confidence||p.unassembled).map(p=><div key={p.page}>
      <p>{t('ocrPageReview',{page:p.page,low:p.low_confidence,missing:p.unassembled})}</p>
      {(['low_confidence_samples','unassembled_samples'] as const).map(key=>p[key]?.length>0&&<details key={key}>
        <summary>{t(key==='low_confidence_samples'?'ocrUncertainText':'ocrUnassembledText')}</summary>
        {p[key].map((sample:any,i:number)=><p key={i} dir="auto">{sample.text}</p>)}
      </details>)}
    </div>)}
  </details>;
}
