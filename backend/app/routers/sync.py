from fastapi import APIRouter, Query
from app.core.config import API_TICKET
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import save_opportunity

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/market")
def sync_market(
    keyword: str = Query(default=""),
    estado: str = Query(default=""),
    tipo: str = Query(default=""),
    organismo: str = Query(default=""),
    categoria: str = Query(default=""),
    region: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    monto_min: float | None = Query(default=None),
    monto_max: float | None = Query(default=None),
    moneda: str = Query(default=""),
    codigo_externo: str = Query(default=""),
    pagina: int = Query(default=1),
    cantidad: int = Query(default=25),
    orden: str = Query(default=""),
):
    service = MarketSourcesService(ticket=API_TICKET)
    filters = {
        "keyword": keyword,
        "estado": estado,
        "tipo": tipo,
        "organismo": organismo,
        "categoria": categoria,
        "region": region,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "monto_min": monto_min,
        "monto_max": monto_max,
        "moneda": moneda,
        "codigo_externo": codigo_externo,
        "pagina": pagina,
        "cantidad": cantidad,
        "orden": orden,
    }
    opportunities = service.fetch_mercado_publico(keyword=keyword, filters=filters)
    for item in opportunities:
        save_opportunity(item)
    return {"count": len(opportunities), "source": "mercado_publico", "filters": filters}


@router.post("/agile")
def sync_agile(
    keyword: str = Query(default=""),
    categoria: str = Query(default=""),
    estado: str = Query(default=""),
    monto_min: float | None = Query(default=None),
    monto_max: float | None = Query(default=None),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
):
    service = MarketSourcesService(ticket=API_TICKET)
    return {
        "count": 0,
        "source": "compras_agiles",
        "filters": {
            "keyword": keyword,
            "categoria": categoria,
            "estado": estado,
            "monto_min": monto_min,
            "monto_max": monto_max,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    }
