import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import _agile_search_text, _compra_agil_record


def test_compra_agil_changes_page_requests_only_one_page():
    response = MagicMock()
    response.json.return_value = {
        "success": "OK",
        "payload": {"items": [{"codigo": "1-COT26"}], "paginacion": {"total_paginas": 3}},
    }
    with patch("app.services.market_sources.requests.get", return_value=response) as get:
        items, pagination = MarketSourcesService("ticket").fetch_compra_agil_changes_page(
            minutes=1500, page=2, page_size=50,
        )
    assert items == [{"codigo": "1-COT26"}]
    assert pagination["total_paginas"] == 3
    assert get.call_args.kwargs["params"]["numero_pagina"] == 2
    assert get.call_args.kwargs["params"]["ttl_cambio_ms"] == 90_000_000


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


def test_compra_agil_reads_first_and_second_closing_dates():
    code, values = _compra_agil_record({
        "codigo": "123-1-COT26",
        "fechas": {
            "fecha_cierre_primer_llamado": "2026-08-07T15:00:00-04:00",
            "fecha_cierre_segundo_llamado": "2026-08-10T15:00:00-04:00",
        },
    })

    assert code == "123-1-COT26"
    assert values["fecha_primer_cierre"].day == 7
    assert values["fecha_segundo_cierre"].day == 10


def test_compra_agil_search_text_includes_requested_products():
    text = _agile_search_text({
        "productos_solicitados": [{
            "codigo_producto": "10131508",
            "nombre": "Alimento para perros",
            "descripcion": "Uso veterinario",
        }],
    }, "123-COT26", "Compra de insumos", "", "Municipalidad")

    assert "alimento para perros" in text
    assert "uso veterinario" in text
    assert "10131508" in text


def test_compra_agil_search_text_accepts_product_container():
    text = _agile_search_text({
        "productos_solicitados": {
            "items": [{"nombre": "Vacuna antirrábica"}],
        },
    }, "123-COT26", "Compra", "", "Municipalidad")

    assert "vacuna antirrábica" in text
