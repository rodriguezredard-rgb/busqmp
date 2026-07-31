import { useState } from 'react';
import { authConfigured, signIn, signUp } from './auth';

export default function Landing({ onAuthenticated }) {
  const [authOpen, setAuthOpen] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [form, setForm] = useState({ email: '', password: '' });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setLoading(true); setMessage('');
    try {
      const session = registering ? await signUp(form.email, form.password) : await signIn(form.email, form.password);
      if (session.access_token) onAuthenticated(session);
      else setMessage('Revisa tu correo para confirmar la cuenta antes de ingresar.');
    } catch (error) { setMessage(error.message); } finally { setLoading(false); }
  }

  return <div className="landing">
    <nav className="landing-nav"><a className="landing-brand" href="#inicio"><span>BO</span><strong>Oportunidades</strong></a><div><a href="#funciones">Cómo funciona</a><button className="login-button" onClick={() => setAuthOpen(true)}>Ingresar</button></div></nav>
    <main id="inicio" className="hero"><div className="hero-copy"><span className="hero-kicker">Inteligencia comercial · Mercado Público</span><h1>Encuentra oportunidades públicas antes que tu competencia.</h1><p>Centraliza licitaciones y compras ágiles, filtra por los rubros que importan para tu negocio y recibe alertas programadas directamente en tu correo.</p><div className="hero-actions"><button onClick={() => { setRegistering(true); setAuthOpen(true); }}>Comenzar ahora</button><a href="#funciones">Conocer la plataforma</a></div><div className="hero-trust"><span>✓ Datos sincronizados</span><span>✓ Filtros inteligentes</span><span>✓ Alertas por correo</span></div></div><div className="hero-preview"><div className="preview-bar"><i /><i /><i /></div><small>OPORTUNIDADES ACTIVAS</small><strong>Mercado Público, más simple.</strong><div className="preview-metric"><b>4.215</b><span>Licitaciones monitoreadas</span></div><div className="preview-row"><i /><span><b>Servicio de mantenimiento integral</b><small>Región Metropolitana · Cierra mañana</small></span></div><div className="preview-row"><i /><span><b>Adquisición de equipamiento</b><small>Compra Ágil · Publicada hoy</small></span></div></div></main>
    <section id="funciones" className="features"><div><small>TODO EN UN SOLO LUGAR</small><h2>Convierte información pública en oportunidades comerciales.</h2></div><article><span>01</span><h3>Busca</h3><p>Consulta licitaciones y compras ágiles desde una interfaz rápida y ordenada.</p></article><article><span>02</span><h3>Filtra</h3><p>Combina palabras clave, exclusiones, organismos, regiones y rubros oficiales.</p></article><article><span>03</span><h3>Recibe alertas</h3><p>Programa búsquedas y recibe solamente las oportunidades relevantes.</p></article></section>
    <footer className="landing-footer"><strong>Oportunidades</strong><span>Información de Mercado Público para mejores decisiones.</span></footer>
    {authOpen && <div className="auth-overlay" role="dialog" aria-modal="true"><button className="auth-backdrop" aria-label="Cerrar" onClick={() => setAuthOpen(false)} /><section className="auth-card"><button className="auth-close" onClick={() => setAuthOpen(false)}>×</button><span className="auth-mark">BO</span><h2>{registering ? 'Crea tu cuenta' : 'Bienvenido de vuelta'}</h2><p>{registering ? 'Comienza a monitorear oportunidades para tu negocio.' : 'Ingresa para acceder a tus búsquedas y alertas.'}</p>{!authConfigured && <div className="auth-warning">Falta conectar Supabase Auth en Vercel.</div>}<form onSubmit={submit}><label>Correo electrónico<input required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>Contraseña<input required minLength="6" type="password" autoComplete={registering ? 'new-password' : 'current-password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>{message && <div className="auth-message">{message}</div>}<button disabled={loading || !authConfigured}>{loading ? 'Procesando…' : registering ? 'Crear cuenta' : 'Ingresar'}</button></form><button className="auth-switch" onClick={() => { setRegistering(!registering); setMessage(''); }}>{registering ? 'Ya tengo una cuenta' : 'Crear una cuenta nueva'}</button></section></div>}
  </div>;
}
