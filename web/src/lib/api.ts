export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error('登入已逾時或尚未登入，請重新整理並使用 Google 登入。');
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  return response.json();
}
export const jsonRequest = (body: unknown, method = 'POST'): RequestInit => ({method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});

export async function apiList(path: string): Promise<any[]> {
  const result = await api(path);
  if (!Array.isArray(result)) throw new Error('文件清單格式錯誤，請重新整理或聯絡管理員。');
  return result;
}
