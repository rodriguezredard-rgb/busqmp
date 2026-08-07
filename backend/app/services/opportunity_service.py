from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import func, or_
from app.models.database import SessionLocal, initialize_database
import json
from app.models.market_data import CompraAgil, LicitacionActiva, OpportunityCategory


def _datetime(value):
    if not value or isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    # La API v1 de licitaciones entrega fechas sin offset, pero corresponden
    # a la hora local chilena. Se normalizan antes de guardarlas en Supabase.
    if parsed and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("America/Santiago"))
    return parsed


def _keyword_pattern(keyword: str) -> str:
    """Convierte * en comodín y escapa los comodines propios de SQL."""
    escaped = (keyword.replace("\\", "\\\\")
               .replace("%", "\\%")
               .replace("_", "\\_"))
    return f"%{escaped.replace('*', '%')}%"


def _licitacion_dict(row):
    detail = row.source_detail or {}
    buyer = detail.get("Comprador") or {}
    dates = detail.get("Fechas") or {}
    organization = row.organismo or str(buyer.get("NombreOrganismo") or buyer.get("NombreUnidad") or "")
    region = row.region or str(buyer.get("RegionUnidad") or buyer.get("RegionOrganismo") or "")
    description = row.descripcion or str(detail.get("Descripcion") or "")
    publish_date = (_datetime(dates.get("FechaPublicacion") or detail.get("FechaPublicacion"))
                    or row.fecha_publicacion)
    closing_date = (_datetime(dates.get("FechaCierre") or detail.get("FechaCierre"))
                    or row.fecha_cierre)
    raw_amount = detail.get("MontoEstimado")
    try:
        amount = float(raw_amount) if raw_amount not in (None, "") else None
    except (TypeError, ValueError):
        amount = None
    return {
        "id": f"licitacion:{row.codigo}", "source": "mercado_publico",
        "opportunity_type": "licitacion", "external_id": row.codigo,
        "title": row.nombre, "description": description,
        "organization": organization, "category": "", "category_codes": json.loads(row.category_codes or "[]"), "amount": amount,
        "currency": str(detail.get("Moneda") or "CLP"), "publish_date": publish_date,
        "award_date": None, "closing_date": closing_date,
        "status": row.estado, "region": region,
        "url": f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={row.codigo}",
    }


def _agile_dict(row):
    return {
        "id": f"compra_agil:{row.codigo}", "source": "compras_agiles",
        "opportunity_type": "compra_agil", "external_id": row.codigo,
        "title": row.nombre, "description": row.descripcion,
        "organization": row.organismo, "category": "", "category_codes": json.loads(row.category_codes or "[]"), "amount": float(row.monto) if row.monto is not None else None,
        "currency": row.moneda, "publish_date": row.fecha_publicacion,
        "award_date": None,
        "closing_date": row.fecha_segundo_cierre or row.fecha_primer_cierre or row.fecha_cierre,
        "first_closing_date": row.fecha_primer_cierre or row.fecha_cierre,
        "second_closing_date": row.fecha_segundo_cierre,
        "status": row.estado, "region": row.region,
        "url": f"https://buscador.mercadopublico.cl/ficha?code={row.codigo}",
    }


def _agile_closing_dates(data: dict):
    fechas = data.get("fechas") or {}
    primer_cierre = _datetime(
        fechas.get("fecha_primer_cierre")
        or fechas.get("fecha_cierre_primer_llamado")
        or fechas.get("primer_cierre")
        or data.get("fecha_primer_cierre")
    )
    segundo_cierre = _datetime(
        fechas.get("fecha_segundo_cierre")
        or fechas.get("fecha_cierre_segundo_llamado")
        or fechas.get("segundo_cierre")
        or data.get("fecha_segundo_cierre")
    )
    cierre = _datetime(fechas.get("fecha_cierre") or data.get("fecha_cierre"))
    return primer_cierre or cierre, segundo_cierre, cierre


def _agile_search_text(data: dict, code: str, name: str, description: str, organization: str) -> str:
    product_parts = []
    products = data.get("productos_solicitados") or []
    if isinstance(products, dict):
        products = (
            products.get("items")
            or products.get("listado")
            or products.get("productos")
            or list(products.values())
        )
    if not isinstance(products, list):
        products = []
    for product in products:
        if not isinstance(product, dict):
            continue
        product_parts.extend([
            str(product.get("codigo_producto") or ""),
            str(product.get("nombre") or ""),
            str(product.get("descripcion") or ""),
        ])
    return " ".join([code, name, description, organization, *product_parts]).lower()


def _compra_agil_record(data: dict):
    codigo = str(data.get("codigo") or "").strip()
    if not codigo:
        return None, None
    estado = data.get("estado") or {}
    fechas = data.get("fechas") or {}
    primer_cierre, segundo_cierre, cierre = _agile_closing_dates(data)
    montos = data.get("montos") or data.get("presupuesto") or {}
    institucion = data.get("institucion") or {}
    descripcion = str(data.get("descripcion") or "")
    nombre = str(data.get("nombre") or "")
    organismo = str(institucion.get("organismo_comprador") or "")
    values = {
        "nombre": nombre, "descripcion": descripcion,
        "estado": str(estado.get("codigo") or estado.get("glosa") or ""),
        "organismo": organismo,
        "rut_organismo": str(institucion.get("rut") or ""),
        "unidad_compra": str(institucion.get("unidad_compra") or ""),
        "region_codigo": institucion.get("region"), "region": str(institucion.get("nombre_region") or ""),
        "moneda": str(montos.get("moneda") or "CLP"),
        "monto": montos.get("monto_disponible_clp") or montos.get("monto_disponible"),
        "fecha_publicacion": _datetime(fechas.get("fecha_publicacion")),
        "fecha_cierre": cierre,
        "fecha_primer_cierre": primer_cierre or cierre,
        "fecha_segundo_cierre": segundo_cierre,
        "fecha_ultimo_cambio": _datetime(fechas.get("fecha_ultimo_cambio")),
        "search_text": _agile_search_text(data, codigo, nombre, descripcion, organismo),
        "source_detail": data, "updated_at": datetime.now(timezone.utc),
    }
    return codigo, values


def save_compras_agiles(items: list[dict]) -> int:
    initialize_database()
    db = SessionLocal()
    try:
        saved = 0
        for data in items:
            codigo, values = _compra_agil_record(data)
            if not codigo:
                continue
            row = db.get(CompraAgil, codigo)
            if row:
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                db.add(CompraAgil(codigo=codigo, **values))
            saved += 1
        db.commit()
        return saved
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_compra_agil(data: dict) -> None:
    save_compras_agiles([data])


def backfill_agile_closing_dates() -> int:
    """Completa fechas e índice de productos desde el JSON ya almacenado."""
    initialize_database()
    db = SessionLocal()
    try:
        rows = db.query(CompraAgil).all()
        updated = 0
        for row in rows:
            primer_cierre, segundo_cierre, cierre = _agile_closing_dates(row.source_detail or {})
            search_text = _agile_search_text(
                row.source_detail or {}, row.codigo, row.nombre, row.descripcion, row.organismo,
            )
            changed = False
            if row.fecha_primer_cierre is None:
                row.fecha_primer_cierre = primer_cierre or row.fecha_cierre
                changed = True
            if row.fecha_segundo_cierre is None and segundo_cierre is not None:
                row.fecha_segundo_cierre = segundo_cierre
                changed = True
            if cierre and not row.fecha_cierre:
                row.fecha_cierre = cierre
                changed = True
            if row.search_text != search_text:
                row.search_text = search_text
                changed = True
            updated += int(changed)
        db.commit()
        return updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _category_pairs(detail: dict, source: str) -> list[tuple[str, str]]:
    pairs = []
    if source == "licitacion":
        item_container = detail.get("Items") or {}
        items = item_container.get("Listado") or [] if isinstance(item_container, dict) else []
        for item in items:
            code = str(item.get("CodigoCategoria") or item.get("CodigoProducto") or "").strip()
            name = str(item.get("Categoria") or item.get("NombreProducto") or "").strip()
            if code and name:
                pairs.append((code, name))
    else:
        for item in detail.get("productos_solicitados") or []:
            code = str(item.get("codigo_producto") or "").strip()
            name = str(item.get("nombre") or item.get("descripcion") or "").strip()
            if code and name:
                pairs.append((code, name))
    return list(dict.fromkeys(pairs))


def save_opportunity_categories(code: str, detail: dict, source: str) -> int:
    initialize_database()
    pairs = _category_pairs(detail, source)
    db = SessionLocal()
    try:
        model = LicitacionActiva if source == "licitacion" else CompraAgil
        row = db.get(model, code)
        if not row:
            return 0
        row.category_codes = json.dumps([item[0] for item in pairs], ensure_ascii=False)
        row.category_names = json.dumps([item[1] for item in pairs] or ["Sin categoría disponible"], ensure_ascii=False)
        row.source_detail = detail
        if source == "licitacion":
            buyer = detail.get("Comprador") or {}
            dates = detail.get("Fechas") or {}
            row.descripcion = str(detail.get("Descripcion") or row.descripcion or "")
            row.organismo = str(buyer.get("NombreOrganismo") or buyer.get("NombreUnidad") or "No informado")
            row.region = str(buyer.get("RegionUnidad") or buyer.get("RegionOrganismo") or "")
            row.fecha_publicacion = _datetime(dates.get("FechaPublicacion") or detail.get("FechaPublicacion"))
            row.fecha_cierre = (_datetime(dates.get("FechaCierre") or detail.get("FechaCierre"))
                                or row.fecha_cierre)
            row.search_text = " ".join([
                row.codigo, row.nombre, row.descripcion, row.organismo,
            ]).lower()
        else:
            row.search_text = _agile_search_text(
                detail, row.codigo, row.nombre, row.descripcion, row.organismo,
            )
        now = datetime.now(timezone.utc)
        for category_code, category_name in pairs:
            category = db.get(OpportunityCategory, category_code)
            if category:
                category.name, category.updated_at = category_name, now
            else:
                db.add(OpportunityCategory(code=category_code, name=category_name, source=source, updated_at=now))
        db.commit()
        return len(pairs)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_categories(search: str = "", limit: int = 200):
    db = SessionLocal()
    try:
        query = db.query(OpportunityCategory)
        if search:
            query = query.filter(OpportunityCategory.name.ilike(f"%{search}%"))
        return [{"code": row.code, "name": row.name, "source": row.source}
                for row in query.order_by(OpportunityCategory.name).limit(limit).all()]
    finally:
        db.close()


def list_unenriched_codes(source: str, limit: int = 5) -> list[str]:
    initialize_database()
    db = SessionLocal()
    try:
        model = LicitacionActiva if source == "licitacion" else CompraAgil
        query = db.query(model).filter(model.category_names == "[]")
        if source == "licitacion":
            query = db.query(model).filter(or_(
                model.category_names == "[]",
                model.organismo == "",
            ))
            query = query.filter(LicitacionActiva.activa.is_(True))
        if source == "licitacion":
            query = query.order_by(LicitacionActiva.fecha_cierre.asc())
        return [row.codigo for row in query.limit(limit).all()]
    finally:
        db.close()


def sync_active_licitaciones(items: list[dict]) -> int:
    """Reemplaza lógicamente el inventario activo sin borrar su historial."""
    initialize_database()
    if not items:
        return 0
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        rows = []
        for data in items:
            codigo = str(data.get("CodigoExterno") or "").strip()
            if not codigo:
                continue
            comprador = data.get("Comprador") or {}
            fechas = data.get("Fechas") or {}
            nombre = str(data.get("Nombre") or "")
            descripcion = str(data.get("Descripcion") or "")
            organismo = str(comprador.get("NombreOrganismo") or "")
            rows.append({
                "codigo": codigo,
                "nombre": nombre, "descripcion": descripcion,
                "estado": str(data.get("Estado") or "publicada"),
                "organismo": organismo, "region": str(comprador.get("RegionUnidad") or ""),
                "fecha_publicacion": _datetime(fechas.get("FechaPublicacion") or data.get("FechaPublicacion")),
                "fecha_cierre": _datetime(fechas.get("FechaCierre") or data.get("FechaCierre")),
                "activa": True,
                "search_text": " ".join([codigo, nombre, descripcion, organismo]).lower(),
                "source_detail": data, "last_seen_at": now, "updated_at": now,
            })
        if not rows:
            return 0
        db.query(LicitacionActiva).update({LicitacionActiva.activa: False})
        insert_factory = postgresql_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        # El listado de activas es un resumen y suele omitir metadatos. Esos
        # campos provienen del detalle enriquecido y no deben borrarse en el
        # siguiente ciclo de sincronización.
        preserved_detail_columns = {
            "descripcion", "organismo", "region", "fecha_publicacion",
            "search_text", "source_detail",
        }
        update_columns = [key for key in rows[0]
                          if key != "codigo" and key not in preserved_detail_columns]
        for start in range(0, len(rows), 500):
            statement = insert_factory(LicitacionActiva).values(rows[start:start + 500])
            statement = statement.on_conflict_do_update(
                index_elements=[LicitacionActiva.codigo],
                set_={key: getattr(statement.excluded, key) for key in update_columns},
            )
            db.execute(statement)
        db.commit()
        return len(rows)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_opportunities(keyword="", opportunity_type="all", region="", organization="", status="",
                       minimum_amount=None, maximum_amount=None, limit=50, offset=0, sort="recent"):
    db = SessionLocal()
    try:
        results = []
        query_limit = 10000 if sort != "recent" else limit + offset
        pattern = _keyword_pattern(keyword)
        if opportunity_type in ("all", "licitacion"):
            now = datetime.now(timezone.utc)
            query = db.query(LicitacionActiva).filter(
                LicitacionActiva.activa.is_(True),
                ~func.lower(LicitacionActiva.estado).like("%cerrad%"),
                or_(LicitacionActiva.fecha_cierre.is_(None), LicitacionActiva.fecha_cierre > now),
            )
            if keyword: query = query.filter(LicitacionActiva.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(LicitacionActiva.region.ilike(f"%{region}%"))
            if organization: query = query.filter(LicitacionActiva.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(LicitacionActiva.estado.ilike(f"%{status}%"))
            results.extend(_licitacion_dict(row) for row in query.order_by(LicitacionActiva.fecha_cierre.asc()).limit(query_limit).all())
        if opportunity_type in ("all", "compra_agil"):
            now = datetime.now(timezone.utc)
            effective_closing = func.coalesce(
                CompraAgil.fecha_segundo_cierre,
                CompraAgil.fecha_primer_cierre,
                CompraAgil.fecha_cierre,
            )
            query = db.query(CompraAgil).filter(
                ~func.lower(CompraAgil.estado).like("%cerrad%"),
                or_(effective_closing.is_(None), effective_closing > now),
            )
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
            if organization: query = query.filter(CompraAgil.organismo.ilike(f"%{organization}%"))
            if status:
                query = query.filter(CompraAgil.estado.ilike(f"%{status}%"))
            if minimum_amount is not None: query = query.filter(CompraAgil.monto >= minimum_amount)
            if maximum_amount is not None: query = query.filter(CompraAgil.monto <= maximum_amount)
            results.extend(_agile_dict(row) for row in query.order_by(CompraAgil.fecha_ultimo_cambio.desc()).limit(query_limit).all())
        if sort in ("amount_desc", "amount_asc"):
            available = [item for item in results if item.get("amount") is not None]
            unavailable = [item for item in results if item.get("amount") is None]
            available.sort(key=lambda item: float(item["amount"]), reverse=sort == "amount_desc")
            results = available + unavailable
        else:
            results.sort(
                key=lambda item: str(item.get("publish_date") or item.get("award_date") or ""),
                reverse=sort != "oldest",
            )
        return results[offset:offset + limit]
    finally:
        db.close()


def count_opportunities(keyword="", opportunity_type="all", region="", organization="", status="",
                        minimum_amount=None, maximum_amount=None):
    db = SessionLocal()
    try:
        total = 0
        pattern = _keyword_pattern(keyword)
        if opportunity_type in ("all", "licitacion"):
            now = datetime.now(timezone.utc)
            query = db.query(LicitacionActiva).filter(
                LicitacionActiva.activa.is_(True),
                ~func.lower(LicitacionActiva.estado).like("%cerrad%"),
                or_(LicitacionActiva.fecha_cierre.is_(None), LicitacionActiva.fecha_cierre > now),
            )
            if keyword: query = query.filter(LicitacionActiva.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(LicitacionActiva.region.ilike(f"%{region}%"))
            if organization: query = query.filter(LicitacionActiva.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(LicitacionActiva.estado.ilike(f"%{status}%"))
            total += query.count()
        if opportunity_type in ("all", "compra_agil"):
            now = datetime.now(timezone.utc)
            effective_closing = func.coalesce(
                CompraAgil.fecha_segundo_cierre,
                CompraAgil.fecha_primer_cierre,
                CompraAgil.fecha_cierre,
            )
            query = db.query(CompraAgil).filter(
                ~func.lower(CompraAgil.estado).like("%cerrad%"),
                or_(effective_closing.is_(None), effective_closing > now),
            )
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
            if organization: query = query.filter(CompraAgil.organismo.ilike(f"%{organization}%"))
            if status:
                query = query.filter(CompraAgil.estado.ilike(f"%{status}%"))
            if minimum_amount is not None: query = query.filter(CompraAgil.monto >= minimum_amount)
            if maximum_amount is not None: query = query.filter(CompraAgil.monto <= maximum_amount)
            total += query.count()
        return total
    finally:
        db.close()
