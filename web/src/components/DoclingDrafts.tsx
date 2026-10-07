import {useEffect,useState} from 'react';
import {api,jsonRequest} from '../lib/api';
import {ChunkDraftEditor} from './ChunkDraftEditor';
export function DoclingDrafts({document,disabled,onApplied,onJob}:{document:any;disabled:boolean;onApplied:(doc:any)=>void;onJob:(id:string)=>void}) {
  const [proposals,setProposals]=useState<any[]>([]);
  const [preview,setPreview]=useState<any>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const run=async(action:()=>Promise<void>)=>{setBusy(true);setError('');try{await action();}catch(e:any){setError(e.message);}finally{setBusy(false);}};
  useEffect(()=>{setPreview(null);api(`/api/library/${document.id}/docling-drafts`).then(setProposals).catch(e=>setError(e.message));},[document.id,document.draft_revision]);
  return <section className="docling-drafts">
    <h3>依文件結構自動切片</h3>
    <p>依章節與表格產生候選稿；預覽後可套用為草稿，再沿用差異檢查與發布流程。</p>
    {error&&<p role="alert">{error}</p>}
    <button className="btn btn-secondary" disabled={disabled||busy||!document.docling_enabled} onClick={()=>run(async()=>{const job=await api(`/api/library/${document.id}/docling-drafts`,jsonRequest({revision:document.draft_revision}));onJob(job.id);})}>產生 Docling 候選稿</button>
    {!document.docling_enabled&&<p>文件處理服務尚未啟用，已產生的候選稿仍可預覽。</p>}
    {proposals.filter(p=>p.status==='ready').map(p=><div key={p.id}><span>{p.chunks} 片 · {new Date(p.created_at*1000).toLocaleString()}</span><button className="btn" disabled={busy||disabled} onClick={()=>run(async()=>setPreview(await api(`/api/library/${document.id}/docling-drafts/${p.id}`)))}>預覽候選稿</button></div>)}
    {preview&&<div><p>以下是候選稿預覽。套用會保留原草稿快照與目前發布版本；已 review 文件及版本衝突會拒絕套用。</p><ChunkDraftEditor readOnly chunks={preview.chunks} blocks={preview.blocks} onChange={()=>{}}/><button className="btn btn-primary" disabled={disabled||busy} onClick={()=>run(async()=>{onApplied(await api(`/api/library/${document.id}/docling-drafts/apply`,jsonRequest({proposal_id:preview.id,revision:document.draft_revision})));setPreview(null);})}>套用候選稿為新草稿</button><button className="btn" onClick={()=>setPreview(null)}>關閉預覽</button></div>}
  </section>;
}
