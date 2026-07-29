from __future__ import annotations

from datetime import date
from typing import Callable
import requests

API_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"


class MercadoPublicoService:
    def __init__(self, ticket: str):
        self.ticket = ticket
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "PekenV2/1.0"

    def search_awards(
        self,
        start: date,
        end: date,
        keyword: str = "",
        progress: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        if end < start:
            raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")

        params = {
            "ticket": self.ticket,
            "fecha": start.strftime("%d%m%Y"),
            "estado": "adjudicada",
        }
        response = self.session.get(API_URL, params=params, timeout=40)
        response.raise_for_status()
        payload = response.json()

        rows: list[dict] = []
        listado = payload.get("Listado", []) if isinstance(payload, dict) else []
        for item in listado:
            code = str(item.get("CodigoExterno") or "").strip()
            if not code:
                continue
            if keyword and keyword.lower() not in str(item.get("Nombre", "")).lower():
                continue
            rows.append({
                "id": code,
                "nombre": item.get("Nombre", ""),
                "codigo": code,
            })
        return rows
