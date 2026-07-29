# Buscador de oportunidades

Aplicación para almacenar oportunidades públicas en PostgreSQL, buscarlas con
rapidez y enviar resúmenes diarios configurables desde la web.

## Arquitectura

- Frontend: React + Vite, desplegable en Vercel.
- Backend: FastAPI, desplegable en Render o Railway.
- Datos: SQLite en desarrollo y PostgreSQL/Supabase o Neon en producción.
- Automatización: cron protegido que sincroniza y despacha correos pendientes.

## Configuración del frontend

```env
VITE_API_URL=https://direccion-del-backend.example.com
```

Desde la interfaz se pueden crear y editar perfiles con rubro, palabras
incluidas/excluidas, tipo de oportunidad, región, organismo, montos, correo y
hora diaria.

Consulta [backend/README.md](backend/README.md) para el despliegue de la API y el
correo programado.

## Dónde se guardan los datos

- Sin `DATABASE_URL`, el backend usa `backend/app.db` (SQLite local).
- Con `DATABASE_URL`, oportunidades y perfiles se guardan en PostgreSQL. En
  producción se recomienda usar la cadena de conexión de Supabase o Neon.
- La aplicación no guarda datos en Vercel; Vercel aloja solamente el frontend.
- Si comparte la base con Peken, crea únicamente `busqmp_opportunities` y
  `busqmp_search_profiles`; no modifica las tablas propias de Peken.

## Fuente Mercado Público

La integración se encuentra en `backend/app/services/market_sources.py` y usa el
endpoint oficial `servicios/v1/publico/licitaciones.json`. El ticket se entrega al
backend mediante `MERCADO_PUBLICO_TICKET`; nunca debe agregarse al frontend ni al
repositorio.

El archivo `render.yaml` prepara el backend para Render y `vercel.json` construye
automáticamente la aplicación ubicada en `frontend` desde el repositorio raíz.
