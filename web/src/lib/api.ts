export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  return response.json();
}
export const jsonRequest = (body: unknown, method = 'POST'): RequestInit => ({method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
