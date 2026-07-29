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
