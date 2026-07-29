import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.market_sources import MarketSourcesService


def test_build_params_includes_mercado_publico_filters():
    service = MarketSourcesService(ticket="abc123")
    filters = {
        "keyword": "infraestructura",
        "estado": "adjudicada",
        "tipo": "Licitación",
        "organismo": "Municipalidad",
        "categoria": "Servicios",
        "region": "Metropolitana",
        "fecha_desde": "2026-01-01",
        "fecha_hasta": "2026-12-31",
        "monto_min": 1000000,
        "monto_max": 5000000,
        "moneda": "CLP",
        "codigo_externo": "ABC123",
        "pagina": 2,
        "cantidad": 25,
        "orden": "fecha_publicacion_desc",
    }

    params = service.build_mercado_publico_params("infraestructura", filters)

    assert params["ticket"] == "abc123"
    assert params["palabra"] == "infraestructura"
    assert params["estado"] == "adjudicada"
    assert params["tipo"] == "Licitación"
    assert params["organismo"] == "Municipalidad"
    assert params["categoria"] == "Servicios"
    assert params["region"] == "Metropolitana"
    assert params["fecha_desde"] == "2026-01-01"
    assert params["fecha_hasta"] == "2026-12-31"
    assert params["monto_min"] == 1000000
    assert params["monto_max"] == 5000000
    assert params["moneda"] == "CLP"
    assert params["codigo_externo"] == "ABC123"
    assert params["pagina"] == 2
    assert params["cantidad"] == 25
    assert params["orden"] == "fecha_publicacion_desc"
