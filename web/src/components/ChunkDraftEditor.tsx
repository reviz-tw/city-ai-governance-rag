import {useId, useState} from 'react';
import {useLocale} from '../lib/locale';
import {splitChunk} from '../lib/chunks';

export function ChunkDraftEditor({chunks, blocks, onChange}: {chunks:any[]; blocks:any[]; onChange:(chunks:any[])=>void}) {
  const {t} = useLocale();
  const [selected, setSelected] = useState(chunks[0]?.id);
  const [showOriginal, setShowOriginal] = useState(false);
  const sourceId = useId();
  const index = Math.max(0, chunks.findIndex(chunk=>chunk.id===selected));
  const chunk = chunks[index];
  if (!chunk) return null;
  const sourceBlocks = blocks.filter(block=>chunk.refs.some((ref:any)=>ref.block_id===block.id));
  return <div className="chunk-workspace">
    <div className="chunk-navigation">
      <label>{t('draftChunks',{count:chunks.length})}<select value={chunk.id} onChange={event=>setSelected(event.target.value)}>
        {chunks.map((value,i)=><option key={value.id} value={value.id}>{t('chunkPosition',{number:i+1,total:chunks.length})}</option>)}
      </select></label>
      <div className="chunk-navigation-actions">
        <button className="btn btn-secondary" disabled={index===0} onClick={()=>setSelected(chunks[index-1].id)}>{t('previousChunk')}</button>
        <button className="btn btn-secondary" disabled={index===chunks.length-1} onClick={()=>setSelected(chunks[index+1].id)}>{t('nextChunk')}</button>
        <button className="btn btn-secondary" aria-expanded={showOriginal} aria-controls={sourceId} onClick={()=>setShowOriginal(!showOriginal)}>{t(showOriginal?'hideOriginal':'showOriginal')}</button>
      </div>
    </div>
    <div className={`chunk-editing-area ${showOriginal?'with-original':''}`}>
      <div className="chunk-card">
        <label>{t('chunkContent',{number:index+1})}<textarea key={chunk.id} value={chunk.content} dir="auto" onChange={event=>onChange(chunks.map((value,i)=>i===index?{...value,content:event.target.value}:value))}/></label>
        <div className="chunk-detail"><small>{t('characterCount',{count:Array.from(chunk.content).length})} · {chunk.refs.map((ref:any)=>`${ref.block_id} (${t('page')} ${ref.page??'—'})`).join(', ')}</small></div>
        <button className="btn btn-secondary" disabled={index===chunks.length-1} onClick={()=>{
          const next=chunks[index+1];
          onChange([...chunks.slice(0,index),{...chunk,content:chunk.content+'\n\n'+next.content,refs:[...chunk.refs,...next.refs]},...chunks.slice(index+2)]);
        }}>{t('merge')}</button>
        <button className="btn btn-secondary" disabled={chunk.content.trim().length<2} onClick={()=>{
          const parts=splitChunk(chunk,blocks,crypto.randomUUID());
          if(parts)onChange([...chunks.slice(0,index),...parts,...chunks.slice(index+1)]);
        }}>{t('split')}</button>
      </div>
      {showOriginal&&<aside id={sourceId} className="chunk-original"><h3>{t('extracted')}</h3>{sourceBlocks.map(block=><section key={block.id}><small>{block.id} · {t('page')} {block.page??'—'}</small><p dir="auto">{block.text}</p></section>)}</aside>}
    </div>
  </div>;
}
