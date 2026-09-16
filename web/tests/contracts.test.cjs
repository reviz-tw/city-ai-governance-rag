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
