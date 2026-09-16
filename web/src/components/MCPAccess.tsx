import {WorkspacePanel} from './WorkspacePanel';
import {useState} from 'react';
import {api} from '../lib/api';

export function MCPAccess({onClose}:{onClose:()=>void}) {
  const [credential,setCredential]=useState<any>(null);
  const [error,setError]=useState('');
  return <WorkspacePanel title="連到其他 AI 工具（MCP）" onClose={onClose}>
    <p>為你自己的 MCP 用戶端建立一小時憑證。權限與目前帳號相同，僅能用於 MCP；不要分享或貼進對話。新憑證會撤銷上一個。</p>
    <p className="endpoint"><code>{location.origin}/mcp</code></p>
    <button className="btn btn-primary" onClick={async()=>{try {setError('');setCredential(await api('/api/auth/mcp-token',{method:'POST'}));}catch(e:any){setError(e.message);}}}>建立個人短期憑證</button>
    {credential&&<><label>Authorization: Bearer <input type="password" autoComplete="off" readOnly value={credential.token} onFocus={e=>e.target.select()}/></label>
      <button className="btn" onClick={async()=>{try {await navigator.clipboard.writeText(credential.token);}catch{setError('複製失敗，請自行選取欄位複製。');}}}>複製憑證</button>
      <p>有效至 {new Date(credential.expires_at*1000).toLocaleString()}；關閉面板後不保存明文。</p></>}
    <button className="btn" onClick={async()=>{try {await api('/api/auth/mcp-token',{method:'DELETE'});setCredential(null);}catch(e:any){setError(e.message);}}}>撤銷我的 MCP 憑證</button>
    {error&&<p role="alert">{error}</p>}
  </WorkspacePanel>;
}
