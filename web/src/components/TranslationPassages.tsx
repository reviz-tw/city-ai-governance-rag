import {useLocale} from '../lib/locale';
import {ChunkTranslationResult} from '../types';
import {sourceDisplayText} from '../lib/source-display';
import {PanelKey} from '../lib/panel-copy';

const reasons:Record<string,PanelKey>={
  numbers_mismatch:'translationNumbers',links_mismatch:'translationLinks',
  table_structure_mismatch:'translationStructure',empty_output:'translationEmpty',
  output_truncated:'translationTruncated',input_too_large:'translationTruncated',
  model_unavailable:'translationModelUnavailable',worker_interrupted:'translationInterrupted',
  source_changed:'stale',ocr_required:'ocrBlocked',
};

export function TranslationPassages({result}:{result:ChunkTranslationResult}) {
  const {t}=useLocale();
  const completed=result.chunks.filter(c=>c.status==='completed').length;
  return <>
    <p role="status">{t('translationProgress',{done:completed,total:result.chunks.length})}</p>
    {result.chunks.map(chunk=><section className="source-block" key={chunk.chunk_id}>
      <small>{chunk.chunk_id} · {t('page')} {Array.from(new Set(chunk.refs.map(r=>r.page).filter(p=>p!=null))).join(', ')||t('unknownPage')}</small>
      <div className="parallel-text">
        <div dir="auto"><strong>{t('original')}</strong><p className="source-passage">{sourceDisplayText(chunk.original)}</p></div>
        <div dir="auto">
          {chunk.status==='completed'?<p className="source-passage">{sourceDisplayText(chunk.text||'')}</p>:<>
            <p role={['failed','blocked'].includes(chunk.status)?'alert':'status'}>{t(chunk.status==='running'?'translationRunning':chunk.status==='failed'?'translationFailed':chunk.status==='blocked'?'ocrBlocked':'translationWaiting')}</p>
            {chunk.error&&chunk.status!=='blocked'&&<p>{t(reasons[chunk.error]||'translationFailed')}</p>}
          </>}
        </div>
      </div>
    </section>)}
  </>;
}
