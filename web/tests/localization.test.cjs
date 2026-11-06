const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');

// Exercise the actual components and locale provider without a browser or API.
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX},
  }).outputText, file);
}
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {LocaleProvider} = require('../src/lib/locale.tsx');
const {INTERFACE_LANGUAGES} = require('../src/lib/languages.ts');
const {STRINGS} = require('../src/i18n.ts');
const {panelText, panelError, extractionWarningText} = require('../src/lib/panel-copy.ts');
const {ConversationHistory} = require('../src/components/ConversationHistory.tsx');
const {AccountManagement} = require('../src/components/AccountManagement.tsx');
const {DoclingDrafts} = require('../src/components/DoclingDrafts.tsx');
const {Login} = require('../src/components/Login.tsx');
const {Header} = require('../src/components/Header.tsx');
const {ExtractionWarnings} = require('../src/components/ExtractionWarnings.tsx');
const {ChatView} = require('../src/components/ChatView.tsx');
const noop = () => {};
const render = (lang, component, props) => renderToStaticMarkup(React.createElement(LocaleProvider, {lang}, React.createElement(component, props)));
const escaped = text => text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#x27;');

for (const lang of Object.keys(INTERFACE_LANGUAGES)) {
  test(`${lang}: new feature surfaces render in the selected locale`, () => {
    const cases = [
      [ConversationHistory, {current:'saved',busy:false,revision:0,onSelect:noop,onNew:noop}, ['conversationHistory','newConversation','rename','delete']],
      [AccountManagement, {email:'admin@example.test',onClose:noop}, ['accounts','accountIntro','role_reader','role_editor','role_admin','addAccount']],
      [DoclingDrafts, {document:{id:'source',docling_enabled:false},disabled:false,onApplied:noop,onJob:noop}, ['doclingTitle','doclingIntro','doclingGenerate','doclingDisabled']],
      [Login, {onLogin:noop,onLangChange:noop}, ['loginDescription','loginNote']],
      [Header, {t:STRINGS[lang],lang,onLangChange:noop,email:'admin@example.test',loading:false,onLogout:noop,onPanel:noop,admin:true}, ['accounts','tasks']],
      [ExtractionWarnings, {warnings:['OCR_LOW_CONFIDENCE: pages 2, 7']}, ['extractionWarnings']],
    ];
    for (const [component, props, keys] of cases) {
      const html = render(lang, component, props);
      for (const key of keys) assert.ok(html.includes(escaped(panelText(lang,key))), `${component.name}: ${lang}/${key}`);
    }
    const html = render(lang, ChatView, {
      t:STRINGS[lang],lang,loading:false,onSendMessage:noop,onClearHistory:noop,onOpenSource:noop,onArtifact:noop,
      messages:[{id:'a',role:'assistant',content:'User-authored 中文',timestamp:'12:00',error:'回答未完成，可重新提問。',status:'interrupted'}],
    });
    assert.ok(html.includes(escaped(panelText(lang,'answerIncomplete'))));
    assert.ok(html.includes('User-authored 中文')); // Do not translate research content.
    if(lang!=='zh') assert.ok(!html.includes('回答未完成，可重新提問。'));
  });
}

test('OCR warnings translate known codes while preserving pages and unknown diagnostics', () => {
  for(const lang of Object.keys(INTERFACE_LANGUAGES)) {
    for(const code of ['OCR_REQUIRED','OCR_LOW_CONFIDENCE','OCR_LAYOUT_COVERAGE']) {
      const text=extractionWarningText(lang,`${code}: pages 2, 7`);
      assert.ok(text.includes('2, 7'));
      assert.ok(!text.includes(`${code}: pages`));
    }
    assert.notEqual(extractionWarningText(lang,'PDF_LAYOUT_REVIEW: extracted text may not preserve complex tables or images'),'PDF_LAYOUT_REVIEW: extracted text may not preserve complex tables or images');
    assert.equal(extractionWarningText(lang,'FUTURE_CODE: original diagnostic'),'FUTURE_CODE: original diagnostic');
  }
});

test('Account errors keep their meaning rather than using generic conflict text', () => {
  for(const [message,key] of [
    ['Account already exists','accountExists'],
    ['Keep at least one active administrator','keepAdmin'],
    ['Cannot remove your own access or administrator role','keepOwnAccess'],
    ['This account is not enabled for this workspace','accountNotEnabled'],
  ]) assert.equal(panelError({status:409,message}),key);
});

test('Components do not introduce hardcoded visible labels or confirmation messages', () => {
  const violations=[];
  for(const file of fs.readdirSync('src/components').filter(file=>file.endsWith('.tsx'))) {
    const source=ts.createSourceFile(file,fs.readFileSync(`src/components/${file}`,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
    // Product names, language codes and protocol syntax must stay literal.
    const technical=new Set(['Google Slides','zh-TW / en / ja','/mcp','Authorization: Bearer']);
    const humanText=text=>/\p{L}/u.test(text.trim())&&!technical.has(text.trim());
    const visit=node=>{
      if(ts.isJsxText(node)&&humanText(node.text))violations.push(`${file}: ${node.text.trim()}`);
      if(ts.isJsxAttribute(node)&&['aria-label','title','placeholder','alt'].includes(node.name.getText(source))&&node.initializer&&ts.isStringLiteral(node.initializer)&&humanText(node.initializer.text))violations.push(`${file}: ${node.getText(source)}`);
      if(ts.isCallExpression(node)&&ts.isPropertyAccessExpression(node.expression)&&['prompt','confirm'].includes(node.expression.name.text)&&node.arguments[0]&&ts.isStringLiteralLike(node.arguments[0]))violations.push(`${file}: ${node.getText(source)}`);
      ts.forEachChild(node,visit);
    };
    visit(source);
  }
  assert.deepEqual(violations,[]);
});
const {TranslationPassages} = require('../src/components/TranslationPassages.tsx');
for (const lang of Object.keys(INTERFACE_LANGUAGES)) {
  test(`${lang}: saved translations distinguish waiting, running and failed chunks`, () => {
    const chunks = [
      {chunk_id:'ready',original:'Original 20',text:'Translated 20',status:'completed',refs:[]},
      {chunk_id:'queued',original:'Next passage',text:null,status:'queued',refs:[]},
      {chunk_id:'running',original:'Active passage',text:null,status:'running',refs:[]},
      {chunk_id:'failed',original:'Failed passage',text:null,status:'failed',error:'numbers_mismatch',refs:[]},
    ];
    const html=render(lang,TranslationPassages,{result:{version:2,chunks}});
    for (const key of ['translationWaiting','translationRunning','translationFailed','translationNumbers'])
      assert.ok(html.includes(escaped(panelText(lang,key))),`${lang}/${key}`);
    assert.ok(html.includes('Translated 20'));
    assert.ok(html.includes('Original 20'));
    const failed=render(lang,TranslationPassages,{result:{version:2,chunks:[chunks[3]]}});
    assert.ok(!failed.includes(escaped(panelText(lang,'translationRunning'))));
    assert.ok(!failed.includes(escaped(panelText(lang,'translationPartial'))));
  });
}
