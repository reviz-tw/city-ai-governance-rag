import {useEffect,useState} from 'react';
import {api,jsonRequest} from '../lib/api';
import {useLocale} from '../lib/locale';
import {ChunkDraftEditor} from './ChunkDraftEditor';
import {ExtractionWarnings} from './ExtractionWarnings';
export function DoclingDrafts({document,disabled,onApplied,onJob}:{document:any;disabled:boolean;onApplied:(doc:any)=>void;onJob:(id:string)=>void}) {
  const {t,date,error:errorText} = useLocale();
  const [proposals,setProposals]=useState<any[]>([]);
  const [preview,setPreview]=useState<any>(null);
  const [error,setError]=useState<unknown>(null);
  const [busy,setBusy]=useState(false);
  const run=async(action:()=>Promise<void>)=>{setBusy(true);setError(null);try{await action();}catch(e:any){setError(e);}finally{setBusy(false);}};
  useEffect(()=>{setPreview(null);api(`/api/library/${document.id}/docling-drafts`).then(setProposals).catch(e=>setError(e));},[document.id,document.draft_revision]);
  return <section className="docling-drafts">
    <h3>{t('doclingTitle')}</h3>
    <p>{t('doclingIntro')}</p>
    {error != null&&<p role="alert">{errorText(error)}</p>}
    <button className="btn btn-secondary" disabled={disabled||busy||!document.docling_enabled} onClick={()=>run(async()=>{const job=await api(`/api/library/${document.id}/docling-drafts`,jsonRequest({revision:document.draft_revision}));onJob(job.id);})}>{t('doclingGenerate')}</button>
    {!document.docling_enabled&&<p>{t('doclingDisabled')}</p>}
    {proposals.filter(p=>p.status==='ready').map(p=><div key={p.id}><span>{t('proposalChunks',{count:p.chunks})} · {date(p.created_at)}</span><button className="btn" disabled={busy||disabled} onClick={()=>run(async()=>setPreview(await api(`/api/library/${document.id}/docling-drafts/${p.id}`)))}>{t('previewProposal')}</button></div>)}
    {preview&&<div><p>{t('doclingPreviewNote')}</p><ExtractionWarnings warnings={preview.details?.warnings} audit={preview.details?.ocr_audit}/><ChunkDraftEditor readOnly chunks={preview.chunks} blocks={preview.blocks} onChange={()=>{}}/><button className="btn btn-primary" disabled={disabled||busy} onClick={()=>run(async()=>{onApplied(await api(`/api/library/${document.id}/docling-drafts/apply`,jsonRequest({proposal_id:preview.id,revision:document.draft_revision})));setPreview(null);})}>{t('applyProposal')}</button><button className="btn" onClick={()=>setPreview(null)}>{t('closePreview')}</button></div>}
  </section>;
}
