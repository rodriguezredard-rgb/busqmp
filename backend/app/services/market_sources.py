from __future__ import annotations

from datetime import datetime
import requests


class MarketSourcesService:
    def __init__(self, ticket: str | None = None):
        self.ticket = ticket or ""

    def build_mercado_publico_params(self, keyword: str = "", filters: dict | None = None) -> dict:
        filters = filters or {}
        params = {
            "ticket": self.ticket,
            "estado": filters.get("estado") or "adjudicada",
            "fecha": datetime.now().strftime("%d%m%Y"),
            "palabra": keyword or filters.get("keyword") or "",
            "tipo": filters.get("tipo") or "",
            "organismo": filters.get("organismo") or "",
            "categoria": filters.get("categoria") or "",
            "region": filters.get("region") or "",
            "fecha_desde": filters.get("fecha_desde") or "",
            "fecha_hasta": filters.get("fecha_hasta") or "",
            "monto_min": filters.get("monto_min") or "",
            "monto_max": filters.get("monto_max") or "",
            "moneda": filters.get("moneda") or "",
            "codigo_externo": filters.get("codigo_externo") or "",
            "pagina": filters.get("pagina") or 1,
            "cantidad": filters.get("cantidad") or 25,
            "orden": filters.get("orden") or "",
        }
        return {k: v for k, v in params.items() if v not in (None, "", [], {})}

    def fetch_mercado_publico(self, keyword: str = "", filters: dict | None = None) -> list[dict]:
        if not self.ticket:
            return []

        url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
        params = self.build_mercado_publico_params(keyword=keyword, filters=filters)
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json() if response.content else {}
        items = payload.get("Listado", []) if isinstance(payload, dict) else []

        results = []
        for item in items:
            title = str(item.get("Nombre") or "").strip()
            if keyword and keyword.lower() not in title.lower():
                continue
            results.append({
                "source": "mercado_publico",
                "opportunity_type": "licitacion",
                "external_id": str(item.get("CodigoExterno") or ""),
                "title": title,
                "organization": str((item.get("Comprador") or {}).get("NombreOrganismo") or ""),
                "amount": None,
                "currency": None,
                "publish_date": None,
                "award_date": None,
                "status": "adjudicada",
                "details": item,
            })
        return results

    def fetch_active_licitaciones(self) -> list[dict]:
        """Obtiene el inventario vigente de procesos donde aún se puede ofertar."""
        if not self.ticket:
            return []
        url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
        response = requests.get(url, params={"ticket": self.ticket, "estado": "activas"}, timeout=60)
        response.raise_for_status()
        payload = response.json() if response.content else {}
        return payload.get("Listado", []) if isinstance(payload, dict) else []

    def fetch_licitacion_detail(self, code: str) -> dict:
        response = requests.get(
            "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json",
            params={"ticket": self.ticket, "codigo": code}, timeout=40,
        )
        response.raise_for_status()
        items = (response.json() or {}).get("Listado") or []
        return items[0] if items else {}

    def fetch_compra_agil_detail(self, code: str) -> dict:
        response = requests.get(
            f"https://api2.mercadopublico.cl/v2/compra-agil/{code}",
            headers={"ticket": self.ticket}, timeout=40,
        )
        response.raise_for_status()
        data = response.json() or {}
        if data.get("success") != "OK":
            raise RuntimeError(str(data.get("errors") or "Detalle inválido de Compra Ágil"))
        return data.get("payload") or {}

    def fetch_compra_agil(self, keyword: str = "", filters: dict | None = None,
                          minutes: int | None = None, page_size: int | None = None) -> list[dict]:
        if not self.ticket:
            return []
        filters = filters or {}
        minutes = int(minutes or filters.get("minutes") or 60)
        page_size = min(int(page_size or filters.get("page_size") or 50), 50)
        url = "https://api2.mercadopublico.cl/v2/compra-agil"
        page, results = 1, []
        while True:
            response = requests.get(url, headers={"ticket": self.ticket}, params={
                "ttl_cambio_ms": minutes * 60_000, "tamano_pagina": page_size,
                "numero_pagina": page, "ordenar_por": "FechaUltimaModificacion",
            }, timeout=40)
            response.raise_for_status()
            payload = (response.json() or {}).get("payload") or {}
            results.extend(payload.get("items") or [])
            pagination = payload.get("paginacion") or {}
            if page >= int(pagination.get("total_paginas") or 1):
                return results
            page += 1

    def fetch_compra_agil_page(self, *, page: int = 1, page_size: int = 50,
                                published_from: str | None = None,
                                published_to: str | None = None,
                                status: str = "publicada") -> tuple[list[dict], dict]:
        """Obtiene una sola página para mantener cada ejecución bajo el límite serverless."""
        if not self.ticket:
            return [], {"numero_pagina": page, "total_paginas": 0, "total_resultados": 0}
        params = {
            "publicado_desde": published_from,
            "publicado_hasta": published_to,
            "estado": status,
            "tamano_pagina": min(page_size, 50),
            "numero_pagina": page,
            "ordenar_por": "FechaPublicacion",
        }
        response = requests.get(
            "https://api2.mercadopublico.cl/v2/compra-agil",
            headers={"ticket": self.ticket},
            params={key: value for key, value in params.items() if value not in (None, "")},
            timeout=40,
        )
        response.raise_for_status()
        data = response.json() or {}
        if data.get("success") != "OK":
            raise RuntimeError(str(data.get("errors") or "Respuesta inválida de Compra Ágil"))
        payload = data.get("payload") or {}
        return payload.get("items") or [], payload.get("paginacion") or {}
