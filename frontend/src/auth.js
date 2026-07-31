// Vite incorpora estas variables públicas al crear cada deployment nuevo.
const URL = import.meta.env.VITE_SUPABASE_URL;
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
const STORAGE_KEY = 'busqmp_session';

export const authConfigured = Boolean(URL && KEY);

async function request(path, { method = 'POST', body, token } = {}) {
  if (!authConfigured) throw new Error('La autenticación aún no está configurada.');
  const response = await fetch(`${URL}/auth/v1/${path}`, {
    method,
    headers: {
      apikey: KEY,
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = response.status === 204 ? {} : await response.json();
  if (!response.ok) throw new Error(data.msg || data.message || data.error_description || 'No fue posible completar la solicitud.');
  return data;
}

export function storedSession() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
}

export function saveSession(session) {
  if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  else localStorage.removeItem(STORAGE_KEY);
}

export async function signIn(email, password) {
  const session = await request('token?grant_type=password', { body: { email, password } });
  saveSession(session);
  return session;
}

export async function signUp(email, password) {
  const data = await request('signup', { body: { email, password } });
  if (data.access_token) saveSession(data);
  return data;
}

export async function refreshSession(refreshToken) {
  const session = await request('token?grant_type=refresh_token', { body: { refresh_token: refreshToken } });
  saveSession(session);
  return session;
}

export async function updateCredentials(token, values) {
  return request('user', { method: 'PUT', token, body: values });
}

export async function signOut(token) {
  try { await request('logout', { token }); } finally { saveSession(null); }
}
