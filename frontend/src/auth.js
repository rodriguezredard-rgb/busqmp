const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'busqmp_session';

export const authConfigured = Boolean(API);

async function request(path, { method = 'POST', body, token } = {}) {
  const response = await fetch(`${API}/auth/${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = response.status === 204 ? {} : await response.json();
  if (!response.ok) throw new Error(data.detail || data.msg || data.message || data.error_description || 'No fue posible completar la solicitud.');
  return data;
}

export function storedSession() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
}

export function saveSession(session) {
  if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  else localStorage.removeItem(STORAGE_KEY);
}

export function recoverySession() {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  if (params.get('type') !== 'recovery' || !params.get('access_token')) return null;
  const session = {
    access_token: params.get('access_token'), refresh_token: params.get('refresh_token'),
    expires_at: Math.floor(Date.now() / 1000) + Number(params.get('expires_in') || 3600), user: {}, recovery: true,
  };
  saveSession(session);
  window.history.replaceState({}, '', `${window.location.pathname}?recovery=1`);
  return session;
}

export async function signIn(email, password) {
  const session = await request('login', { body: { email, password } });
  saveSession(session);
  return session;
}

export async function signUp(email, password, captchaToken) {
  const data = await request('signup', { body: { email, password, captcha_token: captchaToken } });
  if (data.access_token) saveSession(data);
  return data;
}

export async function authConfig() {
  return request('config', { method: 'GET' });
}

export async function recoverPassword(email, captchaToken) {
  return request('recover', { body: { email, captcha_token: captchaToken } });
}

export async function refreshSession(refreshToken) {
  const session = await request('refresh', { body: { refresh_token: refreshToken } });
  saveSession(session);
  return session;
}

export async function updateCredentials(token, values) {
  return request('credentials', { method: 'PUT', token, body: values });
}

export async function signOut(token) {
  try { await request('logout', { token }); } finally { saveSession(null); }
}
