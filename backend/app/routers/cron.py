from fastapi import APIRouter, Header, HTTPException
from app.core.config import API_TICKET, CRON_SECRET
from app.models.database import SessionLocal, initialize_database
from app.services.digest_service import run_due_digests
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import save_compra_agil, sync_active_licitaciones

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
        agile_items = service.fetch_compra_agil(minutes=30)
        for item in agile_items:
            save_compra_agil(item)
        synchronized["compras_agiles"] = len(agile_items)
    db = SessionLocal()
    try:
        return {"synchronized": synchronized, "results": run_due_digests(db)}
    finally:
        db.close()
