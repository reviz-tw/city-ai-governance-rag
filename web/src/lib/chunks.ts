/** Prefer sentence boundaries; retain original ranges whenever the text is unchanged. */
export function splitChunk(chunk: any, blocks: any[], newId: string) {
  const text: string = chunk.content;
  if (text.trim().length < 2) return null;
  const middle = Math.floor(text.length / 2);
  const boundaries = [...text.matchAll(/[。！？.!?](?:\s|$)|[。！？]|\n+/g)]
    .map(m => m.index! + m[0].length)
    .filter(i => text.slice(0,i).trim() && text.slice(i).trim());
  const cut = boundaries.sort((a,b)=>Math.abs(a-middle)-Math.abs(b-middle))[0] ?? middle;
  if (!text.slice(0,cut).trim() || !text.slice(cut).trim()) return null;
  const byId = new Map(blocks.map(b=>[b.id,b]));
  let cursor = 0;
  const ranges = chunk.refs.map((r:any,i:number)=>{
    const value = byId.get(r.block_id)?.text.slice(r.start,r.end) ?? '';
    const start = cursor; cursor += value.length + (i<chunk.refs.length-1 ? 2 : 0);
    return {ref:r,value,start,end:start+value.length};
  });
  const exact = ranges.map((r:any)=>r.value).join('\n\n') === text;
  const refsFor = (start:number,end:number) => exact ? ranges.flatMap((r:any)=>{
    const from=Math.max(start,r.start), to=Math.min(end,r.end);
    return to>from ? [{...r.ref,start:r.ref.start+from-r.start,end:r.ref.start+to-r.start}] : [];
  }) : chunk.refs;
  // Edited OCR text cannot reliably be aligned; keep the wider original provenance.
  return [{...chunk,content:text.slice(0,cut),refs:refsFor(0,cut)},
    {...chunk,id:newId,content:text.slice(cut),refs:refsFor(cut,text.length)}];
}
