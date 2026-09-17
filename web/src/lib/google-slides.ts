import type {PanelKey} from './panel-copy';

export const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
export const SLIDES_MIME = 'application/vnd.google-apps.presentation';
export const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
const DRIVE = 'https://www.googleapis.com/drive/v3';

export class GoogleSlidesError extends Error {
  constructor(public key: PanelKey) {super(key);}
}

// Must be called directly from a user click, after loading GIS/config in advance.
// Tokens live only in this promise/call chain, never in storage or our backend.
export function authorizeDrive(google: any, clientId: string, email: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const client = google.accounts.oauth2.initTokenClient({
      client_id: clientId, scope: DRIVE_FILE_SCOPE, include_granted_scopes: false,
      login_hint: email, prompt: '',
      callback: (result: any) => {
        if (result.error || !result.access_token || !result.scope?.split(' ').includes(DRIVE_FILE_SCOPE)) {
          reject(new GoogleSlidesError('slidesConsent')); return;
        }
        resolve(result.access_token);
      },
      error_callback: () => reject(new GoogleSlidesError('slidesPopup')),
    });
    client.requestAccessToken();
  });
}

type ExportJob = {id: string; revision: number; title: string; fileName: string};
const appError = (status: number) => new GoogleSlidesError(
  status === 401 ? 'expired' : status === 403 ? 'denied' : status === 409 ? 'stale' : status === 404 ? 'missing' : 'slidesFailed');

export async function exportGoogleSlides(job: ExportJob, token: string, email: string, origin: string): Promise<string> {
  const googleFetch = async (url: string, options: RequestInit = {}) => {
    const response = await fetch(url, {...options, credentials: 'omit', redirect: 'error',
      headers: {...options.headers, Authorization: `Bearer ${token}`}, signal: AbortSignal.timeout(120000)});
    if (!response.ok) throw new GoogleSlidesError(response.status === 401 ? 'slidesTokenExpired' : 'slidesFailed');
    return response;
  };
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${origin}:${job.id}:${job.revision}`));
  const exportKey = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  const run = async () => {
    // Recheck the app session, ownership, current source permissions and versions on every export.
    // The Google bearer token is never attached to these same-origin requests.
    const me = await fetch('/api/auth/me', {credentials: 'same-origin'});
    if (!me.ok) throw appError(me.status);
    if ((await me.json()).email?.toLowerCase() !== email.toLowerCase()) throw new GoogleSlidesError('expired');
    const download = await fetch(`/api/artifacts/${encodeURIComponent(job.id)}/download/${encodeURIComponent(job.fileName)}`, {credentials:'same-origin'});
    if (!download.ok) throw appError(download.status);
    const pptx = await download.blob();

    const about = await (await googleFetch(`${DRIVE}/about?fields=user(emailAddress),importFormats`)).json();
    if (about.user?.emailAddress?.toLowerCase() !== email.toLowerCase()) throw new GoogleSlidesError('slidesAccount');
    if (!about.importFormats?.[PPTX_MIME]?.includes(SLIDES_MIME)) throw new GoogleSlidesError('slidesUnsupported');

    // Reopen this revision's copy without overwriting edits made in Google Slides.
    const query = new URLSearchParams({q:`trashed = false and mimeType = '${SLIDES_MIME}' and appProperties has { key='cityRagExport' and value='${exportKey}' }`,fields:'files(id,mimeType)',pageSize:'1'});
    const existing = await (await googleFetch(`${DRIVE}/files?${query}`)).json();
    const link = (file: any) => {
      if (file.mimeType !== SLIDES_MIME || !/^[\w-]+$/.test(file.id || '')) throw new GoogleSlidesError('slidesFailed');
      return `https://docs.google.com/presentation/d/${file.id}/edit`;
    };
    if (existing.files?.length) return link(existing.files[0]);

    // Drive converts the editable PowerPoint into a native presentation. No sharing permissions change.
    const start = await googleFetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,mimeType', {
      method:'POST', headers:{'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Type':PPTX_MIME,'X-Upload-Content-Length':String(pptx.size)},
      body:JSON.stringify({name:job.title || 'City AI Governance',mimeType:SLIDES_MIME,appProperties:{cityRagExport:exportKey}}),
    });
    const upload = new URL(start.headers.get('Location') || '');
    // Never forward a Google token to a URL supplied by a different origin.
    if (upload.origin !== 'https://www.googleapis.com' || upload.pathname !== '/upload/drive/v3/files') throw new GoogleSlidesError('slidesFailed');
    const result = await googleFetch(upload.href, {method:'PUT', headers:{'Content-Type':PPTX_MIME}, body:pptx});
    return link(await result.json());
  };
  // Serialize clicks from this app's tabs; retries first look for the existing native copy.
  return typeof navigator !== 'undefined' && navigator.locks
    ? navigator.locks.request(`google-slides:${exportKey}`, run) : run();
}
