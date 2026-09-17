import {useLocale} from '../lib/locale';

export function SlideDraftEditor({draft,onChange}:{draft:any;onChange:(value:any)=>void}) {
  const {t,label} = useLocale();
  const update = (index:number, patch:any) => onChange({...draft,slides:draft.slides.map((slide:any,i:number)=>i===index?{...slide,...patch}:slide)});
  const move = (from:number,to:number) => {const slides=[...draft.slides];[slides[from],slides[to]]=[slides[to],slides[from]];onChange({...draft,slides});};
  return <>
    <p className="panel-intro">{t('slideReviewIntro')}</p>
    {draft.coverage_note&&<p role="status">{draft.coverage_note}</p>}
    <label>{t('audienceGoal')}<textarea value={draft.audience_goal} onChange={e=>onChange({...draft,audience_goal:e.target.value})}/></label>
    {draft.slides.map((slide:any,index:number)=><section className="slide-draft" key={index}>
      <div className="slide-draft-heading"><h3>{t('slideNumber',{number:index+1})} · {label(`layout_${slide.layout}`)}</h3>
        <button className="btn" disabled={index===0} aria-label={t('moveSlideUp',{number:index+1})} onClick={()=>move(index,index-1)}>↑</button>
        <button className="btn" disabled={index===draft.slides.length-1} aria-label={t('moveSlideDown',{number:index+1})} onClick={()=>move(index,index+1)}>↓</button>
      </div>
      <label>{t('slideTitle')}<input value={slide.title} onChange={e=>update(index,{title:e.target.value})}/></label>
      <label>{t('takeaway')}<textarea value={slide.takeaway} onChange={e=>update(index,{takeaway:e.target.value})}/></label>
      <label>{t('claimType')}<select value={slide.reasoning} onChange={e=>update(index,{reasoning:e.target.value})}>
        {['evidence','inference','recommendation'].map(type=><option value={type} key={type}>{label(`claim_${type}`)}</option>)}
      </select></label>
      {slide.quote&&<label>{t('sourceQuote')}<textarea value={slide.quote} onChange={e=>update(index,{quote:e.target.value})}/></label>}
      {slide.points?.map((point:any,p:number)=><div className="slide-point" key={p}>
        <input aria-label={t('pointLabel',{number:p+1})} value={point.label} onChange={e=>update(index,{points:slide.points.map((v:any,i:number)=>i===p?{...v,label:e.target.value}:v)})}/>
        <textarea aria-label={t('pointDetail',{number:p+1})} value={point.detail} onChange={e=>update(index,{points:slide.points.map((v:any,i:number)=>i===p?{...v,detail:e.target.value}:v)})}/>
      </div>)}
      {slide.layout==='comparison'&&<div className="slide-table-scroll"><table><thead><tr>{slide.columns.map((column:string,c:number)=><th key={c}>
        <input aria-label={t('columnNumber',{number:c+1})} value={column} onChange={e=>update(index,{columns:slide.columns.map((v:string,i:number)=>i===c?e.target.value:v)})}/>
      </th>)}</tr></thead><tbody>{slide.rows.map((row:string[],r:number)=><tr key={r}>{row.map((cell:string,c:number)=><td key={c}>
        <textarea aria-label={t('tableCell',{row:r+1,column:c+1})} value={cell} onChange={e=>update(index,{rows:slide.rows.map((v:string[],i:number)=>i===r?v.map((text,j)=>j===c?e.target.value:text):v)})}/>
      </td>)}</tr>)}</tbody></table></div>}
      {slide.chart?.points?.map((point:any,p:number)=><div key={p}>
        <input aria-label={t('pointLabel',{number:p+1})} value={point.label} onChange={e=>update(index,{chart:{...slide.chart,points:slide.chart.points.map((v:any,i:number)=>i===p?{...v,label:e.target.value}:v)}})}/>
        <p>{point.value} {point.unit} ({point.period})</p><blockquote>{point.quote}</blockquote>
      </div>)}
      <label>{t('speakerNotes')}<textarea value={slide.notes} onChange={e=>update(index,{notes:e.target.value})}/></label>
      <small>{slide.citations.map((c:any)=>`${c.document_id}/${c.block_id}`).join(' · ')}</small>
    </section>)}
  </>;
}
