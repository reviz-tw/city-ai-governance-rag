const {test} = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const Module = require('node:module');
function load(file) {
  const code = ts.transpileModule(fs.readFileSync(file,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const module = new Module(file); module._compile(code,file); return module.exports;
}
const {readSSE}=load('src/lib/sse.ts');
const {normalizeInterfaceLanguage,INTERFACE_LANGUAGES,CONTENT_LANGUAGES}=load('src/lib/languages.ts');
test('SSE preserves multilingual text split across every byte boundary',async()=>{
  const payload = 'data: '+JSON.stringify({type:'sources',sources:[{language:'fr'}]})+'\n\n'+'data: '+JSON.stringify({type:'chunk',text:'Français 繁體中文 日本語'})+'\n\n'+'data: {"type":"done","status":"completed"}\n\n';
  const bytes = new TextEncoder().encode(payload);
  for (let boundary=1; boundary<bytes.length; boundary++) {
    const stream=new ReadableStream({start(c){c.enqueue(bytes.slice(0,boundary));c.enqueue(bytes.slice(boundary));c.close();}});
    const events=[];for await(const event of readSSE(stream))events.push(event);
    assert.equal(events[1].text,'Français 繁體中文 日本語');assert.equal(events.length,3);
  }
});
test('SSE rejects truncated streams instead of silently losing text',async()=>{
  const stream=new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('data: {"type":"chunk","text":"hello"}\n\n'));c.close();}});
  await assert.rejects(async()=>{for await(const event of readSSE(stream)){}},/before completion/);
});
test('Unsupported preferences fall back and removed content languages are unavailable',()=>{
  assert.equal(normalizeInterfaceLanguage('ar-SA'),'en');assert.equal(normalizeInterfaceLanguage('zh-TW'),'zh');
  assert.equal(normalizeInterfaceLanguage('fr'),'fr');assert.equal(INTERFACE_LANGUAGES.ar,undefined);assert.equal(CONTENT_LANGUAGES.ar,undefined);
});
const {splitChunk}=load('src/lib/chunks.ts');
test('Chunk split keeps sentence boundaries and original pages/ranges',()=>{
  const blocks=[{id:'p1',page:1,text:'Before AI use, assess privacy risks.'},{id:'p2',page:2,text:'Human review is mandatory.'}];
  const chunk={id:'c1',content:blocks.map(b=>b.text).join('\n\n'),refs:blocks.map(b=>({block_id:b.id,page:b.page,start:0,end:b.text.length}))};
  const parts=splitChunk(chunk,blocks,'c2');
  assert.equal(parts.map(p=>p.content).join(''),chunk.content);
  assert.equal(parts[0].refs[0].page,1);assert.equal(parts[1].refs[0].page,2);
  for(const part of parts)for(const ref of part.refs)assert.ok(ref.start<ref.end);
  assert.equal(splitChunk({...chunk,content:'字'},blocks,'c2'),null);
});
test('Edited text splits without inventing precise source locations',()=>{
  const refs=[{block_id:'p1',page:7,start:0,end:4}];
  const parts=splitChunk({id:'c1',content:'人工修正句子。保留原文來源。',refs},[{id:'p1',text:'原始文字'}],'c2');
  assert.deepEqual(parts[0].refs,refs);assert.deepEqual(parts[1].refs,refs);
});

const {apiList}=load('src/lib/api.ts');
test('Document list reports expired login and invalid payloads instead of array errors',async(t)=>{
  t.mock.method(global,'fetch',async()=>new Response(JSON.stringify({detail:'Sign in with Google to continue'}),{status:401}));
  await assert.rejects(()=>apiList('/api/library'),/登入/);
  global.fetch=async()=>new Response(JSON.stringify({detail:'Unexpected object'}));
  await assert.rejects(()=>apiList('/api/library'),/文件清單格式錯誤/);
  global.fetch=async()=>new Response(JSON.stringify([{id:'doc-1'}]));
  assert.deepEqual(await apiList('/api/library'),[{id:'doc-1'}]);
  global.fetch=async()=>new Response(JSON.stringify({detail:'Collection unavailable'}),{status:503});
  await assert.rejects(()=>apiList('/api/library'),/Collection unavailable/);
});
