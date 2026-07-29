from fastapi import APIRouter, HTTPException, Query
from app.core.config import API_TICKET
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import save_compra_agil, sync_active_licitaciones

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/market")
def sync_market():
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no está configurado")
    items = MarketSourcesService(API_TICKET).fetch_active_licitaciones()
    return {"count": sync_active_licitaciones(items), "source": "licitaciones_activas"}


@router.post("/agile")
def sync_agile(minutes: int = Query(60, ge=5, le=10080), page_size: int = Query(50, ge=1, le=50)):
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no está configurado")
    items = MarketSourcesService(API_TICKET).fetch_compra_agil(minutes=minutes, page_size=page_size)
    for item in items:
        save_compra_agil(item)
    return {"count": len(items), "source": "compras_agiles", "window_minutes": minutes}
