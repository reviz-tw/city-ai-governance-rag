import {WorkspacePanel} from './WorkspacePanel';
import {useState} from 'react';
import {useLocale} from '../lib/locale';
import {api} from '../lib/api';

export function MCPAccess({onClose}:{onClose:()=>void}) {
  const {t, error:errorText, date} = useLocale();
  const [copied,setCopied] = useState(false);
  const [credential,setCredential]=useState<any>(null);
  const [error,setError]=useState('');
  return <WorkspacePanel title={t('mcp')} onClose={onClose}>
    <p>{t('mcpIntro')}</p>
    <p className="endpoint"><code>{location.origin}/mcp</code></p>
    <button className="btn btn-primary" onClick={async()=>{try {setError('');setCredential(await api('/api/auth/mcp-token',{method:'POST'}));}catch(e:any){setError(errorText(e));}}}>{t('createToken')}</button>
    {credential&&<><label>Authorization: Bearer <input type="password" autoComplete="off" readOnly value={credential.token} onFocus={e=>e.target.select()}/></label>
      <button className="btn" onClick={async()=>{try {await navigator.clipboard.writeText(credential.token);setCopied(true);}catch{setError(t('error'));}}}>{t(copied?'copied':'copyToken')}</button>
      <p>{t('tokenExpiry',{date:date(credential.expires_at)})}</p></>}
    <button className="btn" onClick={async()=>{try {await api('/api/auth/mcp-token',{method:'DELETE'});setCredential(null);}catch(e:any){setError(errorText(e));}}}>{t('revokeToken')}</button>
    {error&&<p role="alert">{error}</p>}
  </WorkspacePanel>;
}
