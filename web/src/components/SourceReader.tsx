import {useEffect, useState} from 'react';
import {api, jsonRequest} from '../lib/api';
import {CONTENT_LANGUAGES} from '../lib/languages';
import {JobView} from './ArtifactPanel';
export function SourceReader({id, language, onClose}: {id: string; language: string; onClose: () => void}) {
  const [doc, setDoc] = useState<any>();
  const [target, setTarget] = useState(language);
  const [blocks, setBlocks] = useState<string[]>([]);
  const [ack, setAck] = useState(false);
  const [job, setJob] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {api(`/api/library/${id}`).then(setDoc).catch(e => setError(e.message));}, [id]);
  const translate = async (scope: string) => {
    try {const task = await api('/api/artifacts', jsonRequest({kind:'translation', scope, source_ids:[id], block_ids:scope==='passage'?blocks:[], language:target, acknowledge_extraction_limits:ack})); setJob(task.id);}
    catch (err: any) {setError(err.message);}
  };
  if (job) return <JobView id={job} onClose={() => setJob('')}/>;
  return <section className="workspace-panel"><button onClick={onClose}>關閉</button>{error && <p role="alert">{error}</p>}
    {doc && <><h2>{doc.title}</h2><p>原始語言：{doc.language} · 版本：{doc.original_hash.slice(0,12)}</p>
      <a className="btn" href={`/api/library/${id}/original`}>查看原始文件</a>
      <label>翻譯目標<select value={target} onChange={e => setTarget(e.target.value)}>{Object.entries(CONTENT_LANGUAGES).map(([code,name]) => <option key={code} value={code}>{name}</option>)}</select></label>
      {doc.warnings?.length > 0 && <label><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)}/>已確認文字擷取限制：{doc.warnings.join(' · ')}</label>}
      <p>全文翻譯可能需要數分鐘。AI 輔助譯本不取代原始文件；掃描頁面需先完成 OCR。</p>
      <button className="btn" disabled={!blocks.length} onClick={() => translate('passage')}>翻譯選定段落（{blocks.length}）</button>
      <button className="btn" onClick={() => translate('document')}>翻譯全文</button>
      {doc.blocks.map((b: any) => <div key={b.id} className="source-block" dir="auto"><label><input type="checkbox" checked={blocks.includes(b.id)} onChange={e => setBlocks(e.target.checked ? [...blocks,b.id] : blocks.filter(v=>v!==b.id))}/>{b.id} · 頁碼 {b.page ?? '未提供'}</label><p>{b.text}</p></div>)}
    </>}
  </section>;
}
