# Backend del buscador

## Desarrollo local

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Copia `.env.example` a `.env` y completa sus valores.

## Producción

1. Crea una base PostgreSQL en Supabase, Neon u otro proveedor.
2. Configura `DATABASE_URL` con la cadena PostgreSQL entregada por el proveedor.
3. Despliega esta carpeta en Render o Railway con:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Configura `FRONTEND_URL` con el dominio exacto del frontend.
5. Configura un proveedor SMTP y las variables `SMTP_*`.
6. Genera un valor largo y aleatorio para `CRON_SECRET`.

## Ejecución automática

Un cron externo debe llamar cada 15 minutos:

```http
POST /cron/daily-digests
Authorization: Bearer <CRON_SECRET>
```

La llamada actualiza Mercado Público, detecta los perfiles cuya hora ya llegó y
envía cada perfil una sola vez por día respetando su zona horaria.

Para una instalación pública se debe agregar autenticación de usuarios antes de
permitir que terceros administren perfiles.
