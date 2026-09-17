export class ApiError extends Error {
  constructor(message: string, public status: number) {super(message);}
}

export async function api(path: string, options: RequestInit = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`, response.status);
  }
  return response.json();
}
export const jsonRequest = (body: unknown, method = 'POST'): RequestInit => ({method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});

export async function apiList(path: string): Promise<any[]> {
  const result = await api(path);
  if (!Array.isArray(result)) throw new ApiError('Invalid list response', 502);
  return result;
}
