import { useCallback, useEffect, useState } from 'react';
import { authConfig, authConfigured, recoverPassword, signIn, signUp } from './auth';
import Turnstile from './Turnstile';

export default function Landing({ onAuthenticated }) {
  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', password: '' });
  const [captchaSiteKey, setCaptchaSiteKey] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const onCaptcha = useCallback((token) => setCaptchaToken(token), []);

  useEffect(() => { authConfig().then((data) => setCaptchaSiteKey(data.captcha_site_key || '')).catch(() => {}); }, []);

  function changeMode(nextMode) { setMode(nextMode); setMessage(''); setCaptchaToken(''); }

  async function submit(event) {
    event.preventDefault(); setLoading(true); setMessage('');
    try {
      if (mode === 'recovery') {
        await recoverPassword(form.email, captchaToken);
        setMessage('Te enviamos un enlace para crear una contraseña nueva. Revisa también spam.');
        return;
      }
      const session = mode === 'register'
        ? await signUp(form.email, form.password, captchaToken)
        : await signIn(form.email, form.password, captchaToken);
      if (session.access_token) onAuthenticated(session);
      else setMessage('Revisa tu correo para confirmar la cuenta antes de ingresar.');
    } catch (error) { setMessage(error.message); } finally { setLoading(false); }
  }

  const needsCaptcha = true;
  const title = mode === 'register' ? 'Crea tu cuenta' : mode === 'recovery' ? 'Recupera tu acceso' : 'Bienvenido de vuelta';
  const description = mode === 'register' ? 'Comienza a monitorear oportunidades para tu negocio.' : mode === 'recovery' ? 'Recibirás un enlace seguro para definir una clave nueva.' : 'Ingresa para acceder a tus búsquedas y alertas.';

  return <div className="landing">
    <nav className="landing-nav"><a className="landing-brand" href="#inicio"><span>BO</span><strong>Oportunidades</strong></a><div className="landing-links"><a href="#inicio">Producto</a><a href="#funciones">Cómo funciona</a></div><div className="landing-access"><button className="nav-register" onClick={() => { changeMode('register'); setAuthOpen(true); }}>Crear cuenta</button><button className="login-button" onClick={() => { changeMode('login'); setAuthOpen(true); }}>Ingresar</button></div></nav>
    <main id="inicio" className="hero"><div className="hero-copy"><span className="hero-kicker">Oportunidades que llegan a ti</span><h1>Configura lo que buscas. Recibe las ofertas que importan.</h1><p>Define palabras clave, rubros, organismos y montos de interés. La plataforma monitorea Mercado Público por ti y te envía por correo las licitaciones y compras ágiles que coinciden con tus criterios.</p><div className="hero-actions"><button onClick={() => { changeMode('register'); setAuthOpen(true); }}>Crear mi primera búsqueda</button><a href="#funciones">Ver cómo funciona <span>↓</span></a></div><div className="hero-trust"><span>Monitoreo automático</span><span>Criterios personalizados</span><span>Alertas directas al correo</span></div></div><div className="hero-preview"><div className="preview-bar"><i /><i /><i /><span>Alertas / Nuevas oportunidades</span></div><small>RESUMEN PERSONALIZADO</small><strong>3 nuevas ofertas coinciden con tu búsqueda.</strong><div className="preview-metric"><b>“Servicios de mantenimiento”</b><span>Palabras, rubros y montos configurados por ti</span></div><div className="preview-row"><i /><span><b>Servicio de mantenimiento integral</b><small>Región Metropolitana · Cierra mañana</small></span><em>Coincide</em></div><div className="preview-row"><i /><span><b>Mantenimiento preventivo de equipos</b><small>Compra Ágil · Publicada hoy</small></span><em>Nueva</em></div></div></main>
    <section id="funciones" className="features"><div><small>UN FLUJO MÁS SIMPLE</small><h2>Deja de buscar todos los días.</h2><p>Configura una vez tus intereses comerciales y deja que la plataforma haga el seguimiento continuo.</p></div><article><span>01</span><h3>Define tus criterios</h3><p>Selecciona palabras, exclusiones, rubros, organismos, regiones y rangos de monto.</p></article><article><span>02</span><h3>Monitoreamos por ti</h3><p>Revisamos periódicamente licitaciones y compras ágiles publicadas en Mercado Público.</p></article><article><span>03</span><h3>Recibe oportunidades</h3><p>Las coincidencias relevantes llegan ordenadas a tu correo, listas para evaluar y ofertar.</p></article></section>
    <footer className="landing-footer"><strong>Oportunidades</strong><span>Información de Mercado Público para mejores decisiones.</span></footer>
    {authOpen && <div className="auth-overlay" role="dialog" aria-modal="true"><button className="auth-backdrop" aria-label="Cerrar" onClick={() => setAuthOpen(false)} /><section className="auth-card"><button className="auth-close" onClick={() => setAuthOpen(false)}>×</button><span className="auth-mark">BO</span><h2>{title}</h2><p>{description}</p>{!authConfigured && <div className="auth-warning">Falta conectar el servicio de autenticación.</div>}<form onSubmit={submit}><label>Correo electrónico<input required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>{mode !== 'recovery' && <label>Contraseña<input required minLength="6" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>}{needsCaptcha && <Turnstile siteKey={captchaSiteKey} onToken={onCaptcha} />}{message && <div className="auth-message">{message}</div>}<button disabled={loading || !authConfigured || (needsCaptcha && !captchaToken)}>{loading ? 'Procesando…' : mode === 'register' ? 'Crear cuenta' : mode === 'recovery' ? 'Enviar enlace seguro' : 'Ingresar'}</button></form>{mode === 'login' && <button className="auth-switch" onClick={() => changeMode('recovery')}>Olvidé mi contraseña</button>}<button className="auth-switch" onClick={() => changeMode(mode === 'register' ? 'login' : 'register')}>{mode === 'register' ? 'Ya tengo una cuenta' : 'Crear una cuenta nueva'}</button></section></div>}
  </div>;
}
