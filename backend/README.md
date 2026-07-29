# Backend del buscador

## Desarrollo local

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Copia `.env.example` a `.env` y completa sus valores.

## Producción gratuita en Vercel

1. En Vercel crea un segundo proyecto desde el mismo repositorio.
2. Configura `backend` como **Root Directory**.
3. No cambies Build Command ni Output Directory; Vercel detectará `app.py`.
4. Configura `DATABASE_URL`, `MERCADO_PUBLICO_TICKET`, `FRONTEND_URL`,
   `CRON_SECRET` y, cuando corresponda, las variables `SMTP_*`.
5. Después del despliegue comprueba `/health` y `/docs`.

## Ejecución automática

El workflow `.github/workflows/sync-opportunities.yml` llama cada 30 minutos:

```http
POST /cron/daily-digests
Authorization: Bearer <CRON_SECRET>
```

La llamada actualiza Mercado Público, detecta los perfiles cuya hora ya llegó y
envía cada perfil una sola vez por día respetando su zona horaria.

En GitHub configura los secretos `BACKEND_URL` (sin barra final) y
`CRON_SECRET` desde Settings → Secrets and variables → Actions.

Para una instalación pública se debe agregar autenticación de usuarios antes de
permitir que terceros administren perfiles.
