import { useEffect, useRef } from 'react';

let scriptPromise;
function loadScript() {
  if (window.turnstile) return Promise.resolve();
  if (!scriptPromise) scriptPromise = new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true; script.defer = true; script.onload = resolve;
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export default function Turnstile({ siteKey, onToken }) {
  const container = useRef(null);
  useEffect(() => {
    if (!siteKey) return undefined;
    let widgetId; let active = true;
    loadScript().then(() => {
      if (active && container.current) widgetId = window.turnstile.render(container.current, {
        sitekey: siteKey, callback: onToken, 'expired-callback': () => onToken(''), theme: 'auto',
      });
    });
    return () => { active = false; if (widgetId != null && window.turnstile) window.turnstile.remove(widgetId); };
  }, [siteKey, onToken]);
  return siteKey ? <div className="turnstile" ref={container} /> : <div className="auth-warning">CAPTCHA pendiente de configuración.</div>;
}
