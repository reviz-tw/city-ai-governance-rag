const {test} = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const Module = require('node:module');
const moduleUnderTest = new Module('google-slides');
moduleUnderTest._compile(ts.transpileModule(fs.readFileSync('src/lib/google-slides.ts','utf8'), {
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
}).outputText, 'google-slides');
const {authorizeDrive,exportGoogleSlides,DRIVE_FILE_SCOPE,SLIDES_MIME,PPTX_MIME} = moduleUnderTest.exports;
const email = 'editor@example.test';
const job = {id:'job-123',revision:3,title:'Governance review',fileName:'slides.pptx'};
const json = data => new Response(JSON.stringify(data));
function mockDrive(t, options = {}) {
  const calls = [];
  t.mock.method(global, 'fetch', async (url, init = {}) => {
    calls.push({url,init});
    if (url === '/api/auth/me') return json({email:options.sessionEmail || email});
    if (url.startsWith('/api/artifacts/')) return options.downloadStatus ? new Response('',{status:options.downloadStatus}) : new Response('editable-pptx');
    if (url.includes('/about?')) return json({user:{emailAddress:options.driveEmail || email},importFormats:{[PPTX_MIME]:options.unsupported ? [] : [SLIDES_MIME]}});
    if (url.includes('/files?q=')) return json({files:options.existing ? [{id:'saved-native-copy',mimeType:SLIDES_MIME}] : []});
    if (init.method === 'POST') return new Response('',{headers:{Location:options.uploadUrl || 'https://www.googleapis.com/upload/drive/v3/files?upload_id=test-session'}});
    if (init.method === 'PUT') {
      if (options.failedUpload) throw new Error('Connection interrupted');
      if (options.expiredToken) return new Response('',{status:401});
      return json({id:'new-native-copy',mimeType:options.wrongMime ? PPTX_MIME : SLIDES_MIME});
    }
    throw new Error(`Unexpected request ${url}`);
  });
  return calls;
}
test('Requests only drive.file and starts OAuth popup synchronously from the click', async () => {
  let settings, requested = false;
  const google = {accounts:{oauth2:{initTokenClient(config){settings = config; return {requestAccessToken(){requested = true;}};}}}};
  const grant = authorizeDrive(google,'public-client',email);
  assert.equal(requested,true);
  assert.equal(settings.scope,DRIVE_FILE_SCOPE);
  assert.equal(settings.include_granted_scopes,false);
  assert.equal(settings.login_hint,email);
  settings.callback({access_token:'test-only-token',scope:DRIVE_FILE_SCOPE});
  assert.equal(await grant,'test-only-token');
  const denied = authorizeDrive(google,'public-client',email);
  settings.callback({access_token:'test-only-token',scope:'openid email'});
  await assert.rejects(denied,err => err.key === 'slidesConsent');
  const closed = authorizeDrive(google,'public-client',email);
  settings.error_callback({type:'popup_closed'});
  await assert.rejects(closed,err => err.key === 'slidesPopup');
});
test('Creates native Slides from the authorized PPTX without sending Google credentials to our backend',async t => {
  const calls = mockDrive(t);
  assert.equal(await exportGoogleSlides(job,'test-only-token',email,'https://app.example'), 'https://docs.google.com/presentation/d/new-native-copy/edit');
  for (const {url,init} of calls) {
    if (url.startsWith('/')) {
      assert.equal(init.credentials,'same-origin'); assert.equal(init.headers,undefined);
    } else {
      assert.equal(init.headers.Authorization,'Bearer test-only-token');
      assert.equal(init.credentials,'omit'); assert.equal(init.redirect,'error');
    }
  }
  const metadata = JSON.parse(calls.find(c => c.init.method === 'POST').init.body);
  assert.equal(metadata.mimeType,SLIDES_MIME); assert.equal(metadata.name,job.title);
  assert.match(metadata.appProperties.cityRagExport,/^[0-9a-f]{64}$/);
  assert.equal(metadata.permissions,undefined);
  const upload = calls.find(c => c.init.method === 'PUT');
  assert.equal(upload.init.headers['Content-Type'],PPTX_MIME);
  assert.equal(await upload.init.body.text(),'editable-pptx');
});
test('Reuses an existing native copy without overwriting user edits or re-uploading',async t => {
  const calls = mockDrive(t,{existing:true});
  assert.match(await exportGoogleSlides(job,'test-token',email,'https://app.example'),/saved-native-copy/);
  assert.equal(calls.some(c => ['POST','PUT'].includes(c.init.method)),false);
});
for (const [name,options,key] of [
  ['wrong Google account',{driveEmail:'other@example.test'},'slidesAccount'],
  ['changed app session',{sessionEmail:'other@example.test'},'expired'],
  ['revoked source access',{downloadStatus:403},'denied'],
  ['updated source',{downloadStatus:409},'stale'],
  ['expired output',{downloadStatus:404},'missing'],
  ['unsupported conversion',{unsupported:true},'slidesUnsupported'],
]) test(`Does not create a file for ${name}`,async t => {
  const calls = mockDrive(t,options);
  await assert.rejects(exportGoogleSlides(job,'test-token',email,'https://app.example'),err => err.key === key);
  assert.equal(calls.some(c => c.init.method === 'POST'),false);
});
test('Rejects upload locations outside Google before exposing a bearer token',async t => {
  const calls = mockDrive(t,{uploadUrl:'https://attacker.example/upload/drive/v3/files'});
  await assert.rejects(exportGoogleSlides(job,'test-token',email,'https://app.example'),err => err.key === 'slidesFailed');
  assert.equal(calls.some(c => c.url.includes('attacker.example')),false);
});
test('Does not report PowerPoint-only imports as native Slides',async t => {
  mockDrive(t,{wrongMime:true});
  await assert.rejects(exportGoogleSlides(job,'test-token',email,'https://app.example'),err => err.key === 'slidesFailed');
});
test('Reports expired authorization and never blindly retries an uncertain upload',async t => {
  let calls = mockDrive(t,{expiredToken:true});
  await assert.rejects(exportGoogleSlides(job,'test-token',email,'https://app.example'),err => err.key === 'slidesTokenExpired');
  assert.equal(calls.filter(c => c.init.method === 'PUT').length,1);
  calls = mockDrive(t,{failedUpload:true});
  await assert.rejects(exportGoogleSlides(job,'test-token',email,'https://app.example'));
  assert.equal(calls.filter(c => c.init.method === 'POST').length,1);
});
