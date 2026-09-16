import {useEffect, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {JobView} from './ArtifactPanel';
import {splitChunk} from '../lib/chunks';
export function Library({editor, onClose, onRead}: {editor: boolean; onClose: () => void; onRead: (id:string)=>void}) {
  const [docs, setDocs] = useState<any[]>([]);
  const [doc, setDoc] = useState<any>(null);
  const [error, setError] = useState('');
  const [file, setFile] = useState<File|null>(null);
  const [rights, setRights] = useState(false);
  const [cleaned, setCleaned] = useState('');
  const [job, setJob] = useState('');
  const [diff, setDiff] = useState('');
  const [diffHash, setDiffHash] = useState('');
  const [savedDraft, setSavedDraft] = useState('');
  const [indexed, setIndexed] = useState<any>(null);
  const [language,setLanguage] = useState('');
  const [city,setCity] = useState('');
  const loadDoc=(value:any)=>{setDoc(value);setSavedDraft(JSON.stringify(value.draft));setDiff('');setDiffHash('');setIndexed(null);};
  const dirty=doc && JSON.stringify(doc.draft)!==savedDraft;
  useEffect(()=>setDiffHash(''),[doc]);
  const refresh = () => api('/api/library').then(setDocs).catch(e=>setError(e.message));
  useEffect(()=>{void refresh();}, []);
  const save = async (reset=false) => {
    try {
      const result = await api(`/api/library/${doc.id}/draft`, jsonRequest({revision:doc.draft_revision, chunks:doc.draft, reset}));
      loadDoc(result); setDiff('已儲存草稿，尚未發布或更新搜尋索引。');
    } catch(e:any){setError(e.message);}
  };
  if(job) return <JobView id={job} onClose={()=>{setJob(''); void refresh();if(doc)void api(`/api/library/${doc.id}`).then(loadDoc).catch(e=>setError(e.message));}}/>;
  return <section className="workspace-panel"><div className="flex justify-between"><h2>來源文件庫</h2><button onClick={onClose}>關閉</button></div>
    {error && <p role="alert">{error}</p>}
    {editor && <details><summary>新增文件</summary><input type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>setFile(e.target.files?.[0]||null)}/>
      <label>原文語言（留空自動偵測）<input value={language} onChange={e=>setLanguage(e.target.value)} placeholder="zh-TW / en / ja"/></label>
      <label>研究城市（選填）<input value={city} onChange={e=>setCity(e.target.value)}/></label>
      <label>清理後文字（選填；另存為草稿，不覆寫原文）<textarea value={cleaned} onChange={e=>setCleaned(e.target.value)}/></label>
      <label><input type="checkbox" checked={rights} onChange={e=>setRights(e.target.checked)}/>已確認可處理、翻譯並依設定分享此文件</label>
      <button className="btn" disabled={!file||!rights} onClick={async()=>{if(!file)return;try{const form=new FormData();form.append('file',file);form.append('rights_confirmed','true');form.append('language',language);form.append('city',city);if(cleaned)form.append('cleaned_text',cleaned);const d=await api('/api/library',{method:'POST',body:form});loadDoc(await api(`/api/library/${d.id}`));await refresh();}catch(e:any){setError(e.message);}}}>上傳並建立草稿</button>
    </details>}
    {docs.map(d=><div key={d.id} className="source-block"><strong>{d.title}</strong><p>{d.language} · {d.index_status} · v{d.published_version}</p><button className="btn" onClick={()=>onRead(d.id)}>原文／翻譯</button>{d.editable&&<button className="btn" onClick={async()=>{try{loadDoc(await api(`/api/library/${d.id}`));}catch(e:any){setError(e.message);}}}>修正草稿</button>}</div>)}
    {doc && editor && <div><h3>{doc.title} · 草稿修訂 {doc.draft_revision}</h3><p>索引狀態：{doc.index_status}；發布版本：{doc.published_version}</p>
      <div className="parallel-text"><div><h3>原始擷取</h3>{doc.blocks?.map((b:any)=><p key={b.id} dir="auto">{b.id} · 頁 {b.page??"—"} · {b.text}</p>)}</div><div><h3>切片草稿</h3>{doc.draft?.map((c:any,i:number)=><div key={c.id}><small>{c.id} · {c.refs.map((r:any)=>`${r.block_id}（頁 ${r.page??'—'}）`).join(', ')}</small><textarea value={c.content} dir="auto" onChange={e=>setDoc({...doc,draft:doc.draft.map((v:any,j:number)=>i===j?{...v,content:e.target.value}:v)})}/>
        <button disabled={i===doc.draft.length-1} onClick={()=>{const next=doc.draft[i+1];const merged={...c,content:c.content+'\n\n'+next.content,refs:[...c.refs,...next.refs]};setDoc({...doc,draft:[...doc.draft.slice(0,i),merged,...doc.draft.slice(i+2)].map((v:any,order:number)=>({...v,order}))});}}>與下一片合併</button>
        <button disabled={c.content.trim().length<2} onClick={()=>{const parts=splitChunk(c,doc.blocks,crypto.randomUUID());if(parts)setDoc({...doc,draft:[...doc.draft.slice(0,i),...parts,...doc.draft.slice(i+1)].map((v:any,order:number)=>({...v,order}))});}}>拆分為兩片</button>
      </div>)}</div></div>
      <button className="btn" onClick={()=>save()}>儲存草稿</button><button className="btn" onClick={()=>save(true)}>還原自動切片</button>
      {dirty&&<p>有尚未儲存的修改。請先儲存，再檢查差異與發布。</p>}
      <button className="btn" disabled={dirty} onClick={async()=>{try{const d=await api(`/api/library/${doc.id}/diff`);setDiff(d.diff||'內容與目前發布版本相同。');setDiffHash(d.hash);}catch(e:any){setError(e.message);}}}>查看發布差異</button>
      <label><input type="checkbox" checked={doc.shared} onChange={async e=>{try{setDoc(await api(`/api/library/${doc.id}/sharing`,jsonRequest({shared:e.target.checked,readers:doc.readers,revision:doc.draft_revision},'PATCH')));}catch(e:any){setError(e.message);}}}/>所有已登入使用者可讀取</label>
      {!doc.indexing_enabled&&<p>切片發布尚未啟用；草稿可以先儲存。</p>}
      {doc.indexing_enabled&&<p>發布後將更新搜尋索引，預計約 10～30 分鐘，實際依索引狀態而定。驗證完成前仍使用前一發布版本。</p>}
      <button className="btn btn-primary" disabled={!doc.indexing_enabled||dirty||!diffHash} onClick={async()=>{try{const task=await api(`/api/library/${doc.id}/publish`,jsonRequest({revision:doc.draft_revision,reviewed_diff:diffHash}));setJob(task.id);}catch(e:any){setError(e.message);}}}>確認差異並發布</button>
      <button className="btn" disabled={!doc.indexing_enabled||doc.published_version<2} onClick={async()=>{try{const task=await api(`/api/library/${doc.id}/rollback`,jsonRequest({revision:doc.draft_revision}));setJob(task.id);}catch(e:any){setError(e.message);}}}>回復前一發布版本</button>
      <button className="btn" disabled={!doc.published_version} onClick={async()=>{try{setIndexed(await api(`/api/library/${doc.id}/indexed-chunks`));}catch(e:any){setError(e.message);}}}>核對實際索引內容</button>
      {indexed&&<div><h3>實際索引 v{indexed.version} · {indexed.verified?'符合發布內容':'尚未符合發布內容'}</h3>{indexed.chunks.map((c:any)=><p key={c.id} dir="auto">{c.id} · {c.content}</p>)}</div>}
      {diff&&<pre className="whitespace-pre-wrap">{diff}</pre>}
    </div>}
  </section>;
}
