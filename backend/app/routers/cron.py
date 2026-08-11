import json
from types import SimpleNamespace
from fastapi import APIRouter, Header, HTTPException, Query
from app.core.config import API_TICKET, CRON_SECRET
from app.models.database import SessionLocal, initialize_database
from app.models.search_profile import SearchProfile
from app.services.digest_service import matching_opportunities, run_due_digests, send_digest
from app.services.market_sources import MarketSourcesService
from app.services.opportunity_service import (
    backfill_agile_closing_dates, list_unenriched_codes, save_compras_agiles,
    save_opportunity_categories, sync_active_licitaciones, count_opportunities,
)

router = APIRouter(prefix="/cron", tags=["cron"])


def _authorize(authorization: str | None):
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "No autorizado")


@router.post("/daily-digests")
def daily_digests(authorization: str | None = Header(default=None)):
    """Compatibilidad: el workflow nuevo usa los endpoints por lote."""
    _authorize(authorization)
    initialize_database()
    backfill_agile_closing_dates()
    synchronized = {"licitaciones_activas": 0, "compras_agiles": 0}
    if API_TICKET:
        service = MarketSourcesService(API_TICKET)
        active_items = service.fetch_active_licitaciones()
        synchronized["licitaciones_activas"] = sync_active_licitaciones(active_items)
        # El workflow corre una vez al día. La ventana de 25 horas deja una
        # hora de solapamiento para absorber retrasos; el upsert la hace segura.
        agile_items = service.fetch_compra_agil(minutes=1500)
        synchronized["compras_agiles"] = save_compras_agiles(agile_items)
    db = SessionLocal()
    try:
        results = run_due_digests(db)
        response = {"synchronized": synchronized, "results": results}
        failed = [item for item in results if item.get("status") in {"error", "invalid_timezone"}]
        if failed:
            raise HTTPException(502, detail=response)
        return response
    finally:
        db.close()


@router.post("/sync-licitaciones")
def sync_licitaciones(authorization: str | None = Header(default=None)):
    _authorize(authorization)
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no esta configurado")
    items = MarketSourcesService(API_TICKET).fetch_active_licitaciones()
    return {"saved": sync_active_licitaciones(items)}


@router.post("/sync-agile-page")
def sync_agile_page(
    page: int = Query(1, ge=1),
    minutes: int = Query(1500, ge=60, le=2880),
    page_size: int = Query(50, ge=1, le=50),
    authorization: str | None = Header(default=None),
):
    _authorize(authorization)
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no esta configurado")
    items, pagination = MarketSourcesService(API_TICKET).fetch_compra_agil_changes_page(
        minutes=minutes, page=page, page_size=page_size,
    )
    return {
        "saved": save_compras_agiles(items),
        "page": int(pagination.get("numero_pagina") or page),
        "total_pages": int(pagination.get("total_paginas") or 0),
        "total_results": int(pagination.get("total_resultados") or 0),
    }


@router.post("/send-due-digests")
def send_due_digest_emails(authorization: str | None = Header(default=None)):
    _authorize(authorization)
    initialize_database()
    backfill_agile_closing_dates()
    db = SessionLocal()
    try:
        results = run_due_digests(db)
        response = {"results": results}
        failed = [item for item in results if item.get("status") in {"error", "invalid_timezone"}]
        if failed:
            raise HTTPException(502, detail=response)
        return response
    finally:
        db.close()


@router.post("/test-digest")
def test_digest(recipient: str, authorization: str | None = Header(default=None)):
    """Envía una prueba inmediata sin consumir el envío diario del perfil."""
    _authorize(authorization)
    initialize_database()
    db = SessionLocal()
    try:
        profiles = db.query(SearchProfile).filter(
            SearchProfile.enabled.is_(True),
            SearchProfile.recipient_email.ilike(recipient.strip()),
        ).all()
        if not profiles:
            raise HTTPException(404, "No hay perfiles habilitados para el destinatario")
        results = []
        for profile in profiles:
            rows = matching_opportunities(profile)
            send_digest(profile, rows)
            results.append({"profile_id": profile.id, "status": "sent", "count": len(rows)})
        return {"results": results}
    finally:
        db.close()


@router.get("/profile-diagnostics")
def profile_diagnostics(recipient: str, authorization: str | None = Header(default=None)):
    """Resume configuración y resultados sin exponer correo ni palabras clave."""
    _authorize(authorization)
    initialize_database()
    backfill_agile_closing_dates()
    db = SessionLocal()
    try:
        profiles = db.query(SearchProfile).filter(
            SearchProfile.recipient_email.ilike(recipient.strip()),
        ).order_by(SearchProfile.id).all()
        summaries = []
        for profile in profiles:
            included_keywords = json.loads(profile.include_keywords or "[]")
            relaxed = SimpleNamespace(
                include_keywords="[]", exclude_keywords="[]", selected_categories="[]",
                opportunity_type="compra_agil", region=profile.region,
                organization=profile.organization, status=profile.status,
                minimum_amount=profile.minimum_amount, maximum_amount=profile.maximum_amount,
            )
            keyword_diagnostics = []
            for index, keyword in enumerate(included_keywords, start=1):
                single_keyword = SimpleNamespace(
                    include_keywords=json.dumps([keyword]), exclude_keywords="[]",
                    selected_categories="[]", opportunity_type="compra_agil",
                    region=profile.region, organization=profile.organization,
                    status=profile.status, minimum_amount=profile.minimum_amount,
                    maximum_amount=profile.maximum_amount,
                )
                keyword_diagnostics.append({
                    "index": index,
                    "uses_wildcard": "*" in keyword,
                    "is_prefix_wildcard": keyword.endswith("*") and keyword.count("*") == 1,
                    "matches": len(matching_opportunities(
                        single_keyword, limit=None, opportunity_type="compra_agil",
                    )),
                })
            summaries.append({
            "id": profile.id,
            "name": profile.name,
            "enabled": profile.enabled,
            "opportunity_type": profile.opportunity_type,
            "include_keyword_count": len(json.loads(profile.include_keywords or "[]")),
            "exclude_keyword_count": len(json.loads(profile.exclude_keywords or "[]")),
            "category_count": len(json.loads(profile.selected_categories or "[]")),
            "has_region_filter": bool(profile.region),
            "has_organization_filter": bool(profile.organization),
            "has_status_filter": bool(profile.status),
            "has_amount_filter": profile.minimum_amount is not None or profile.maximum_amount is not None,
            "matches": len(matching_opportunities(profile, limit=None)),
            "licitacion_matches": len(matching_opportunities(
                profile, limit=None, opportunity_type="licitacion",
            )),
            "compra_agil_matches": len(matching_opportunities(
                profile, limit=None, opportunity_type="compra_agil",
            )),
            "compra_agil_matches_without_keyword_or_category": len(matching_opportunities(
                relaxed, limit=None, opportunity_type="compra_agil",
            )),
            "keyword_diagnostics": keyword_diagnostics,
        })
        return {
            "inventory": {
                "licitaciones": count_opportunities(opportunity_type="licitacion"),
                "compras_agiles": count_opportunities(opportunity_type="compra_agil"),
            },
            "profiles": summaries,
        }
    finally:
        db.close()


@router.post("/disable-profile")
def disable_profile(
    recipient: str, profile_name: str,
    authorization: str | None = Header(default=None),
):
    _authorize(authorization)
    initialize_database()
    db = SessionLocal()
    try:
        profiles = db.query(SearchProfile).filter(
            SearchProfile.recipient_email.ilike(recipient.strip()),
            SearchProfile.name.ilike(profile_name.strip()),
        ).all()
        if len(profiles) != 1:
            raise HTTPException(409, f"Se encontraron {len(profiles)} perfiles coincidentes")
        profiles[0].enabled = False
        db.commit()
        return {"profile_id": profiles[0].id, "name": profiles[0].name, "enabled": False}
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


@router.post("/enrich-categories")
def enrich_categories(
    source: str = Query("licitacion", pattern="^(licitacion|compra_agil)$"),
    limit: int = Query(5, ge=1, le=20),
    authorization: str | None = Header(default=None),
):
    if not CRON_SECRET or authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "No autorizado")
    if not API_TICKET:
        raise HTTPException(503, "MERCADO_PUBLICO_TICKET no está configurado")
    service = MarketSourcesService(API_TICKET)
    results = []
    errors = []
    for code in list_unenriched_codes(source, limit):
        try:
            detail = (service.fetch_licitacion_detail(code) if source == "licitacion"
                      else service.fetch_compra_agil_detail(code))
            results.append({
                "code": code,
                "categories": save_opportunity_categories(code, detail, source),
            })
        except Exception as exc:
            # Una ficha defectuosa o una falla temporal de Mercado Publico no
            # debe abortar el lote completo. No devolvemos el mensaje/URL de
            # la excepcion porque la API de licitaciones lleva el ticket en la URL.
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            errors.append({
                "code": code,
                "status": status_code,
                "error": type(exc).__name__,
            })
    return {
        "source": source,
        "attempted": len(results) + len(errors),
        "processed": len(results),
        "failed": len(errors),
        "errors": errors,
        "results": results,
    }
