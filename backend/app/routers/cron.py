from fastapi import APIRouter, Header, HTTPException, Query
from app.core.config import API_TICKET, CRON_SECRET
from app.models.database import SessionLocal, initialize_database
from app.services.digest_service import run_due_digests
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import save_compra_agil, save_compras_agiles, sync_active_licitaciones

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/daily-digests")
def daily_digests(authorization: str | None = Header(default=None)):
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "No autorizado")
    initialize_database()
    synchronized = {"licitaciones_activas": 0, "compras_agiles": 0}
    if API_TICKET:
        service = MarketSourcesService(API_TICKET)
        active_items = service.fetch_active_licitaciones()
        synchronized["licitaciones_activas"] = sync_active_licitaciones(active_items)
        # El workflow corre cada 30 minutos; una ventana de 60 minutos evita
        # perder cambios si GitHub o Mercado Público se retrasan. El upsert
        # hace que el solapamiento sea seguro.
        agile_items = service.fetch_compra_agil(minutes=60)
        for item in agile_items:
            save_compra_agil(item)
        synchronized["compras_agiles"] = len(agile_items)
    db = SessionLocal()
    try:
        return {"synchronized": synchronized, "results": run_due_digests(db)}
    finally:
        db.close()


@router.post("/agile-backfill-page")
def agile_backfill_page(
    published_from: str,
    published_to: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    authorization: str | None = Header(default=None),
):
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "No autorizado")
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no está configurado")
    items, pagination = MarketSourcesService(API_TICKET).fetch_compra_agil_page(
        page=page, page_size=page_size, published_from=published_from,
        published_to=published_to, status="publicada",
    )
    saved = save_compras_agiles(items)
    return {
        "saved": saved,
        "page": int(pagination.get("numero_pagina") or page),
        "total_pages": int(pagination.get("total_paginas") or 0),
        "total_results": int(pagination.get("total_resultados") or 0),
    }
