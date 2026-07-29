from fastapi import APIRouter, Header, HTTPException
from app.core.config import API_TICKET, CRON_SECRET
from app.models.database import SessionLocal
from app.services.digest_service import run_due_digests
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import save_compra_agil

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/daily-digests")
def daily_digests(authorization: str | None = Header(default=None)):
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "No autorizado")
    synchronized = 0
    if API_TICKET:
        opportunities = MarketSourcesService(API_TICKET).fetch_compra_agil(minutes=30)
        for item in opportunities:
            save_compra_agil(item)
        synchronized = len(opportunities)
    db = SessionLocal()
    try:
        return {"synchronized": synchronized, "results": run_due_digests(db)}
    finally:
        db.close()
