from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.database import SessionLocal, initialize_database
import json
from app.models.market_data import CompraAgil, LicitacionActiva, OpportunityCategory


def _datetime(value):
    if not value or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


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
    publish_date = row.fecha_publicacion or _datetime(dates.get("FechaPublicacion") or detail.get("FechaPublicacion"))
    closing_date = row.fecha_cierre or _datetime(dates.get("FechaCierre") or detail.get("FechaCierre"))
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
        "award_date": None, "closing_date": row.fecha_cierre,
        "status": row.estado, "region": row.region,
        "url": f"https://buscador.mercadopublico.cl/ficha?code={row.codigo}",
    }


def _compra_agil_record(data: dict):
    codigo = str(data.get("codigo") or "").strip()
    if not codigo:
        return None, None
    estado = data.get("estado") or {}
    fechas = data.get("fechas") or {}
    montos = data.get("montos") or data.get("presupuesto") or {}
    institucion = data.get("institucion") or {}
    descripcion = str(data.get("descripcion") or "")
    nombre = str(data.get("nombre") or "")
    values = {
        "nombre": nombre, "descripcion": descripcion,
        "estado": str(estado.get("codigo") or estado.get("glosa") or ""),
        "organismo": str(institucion.get("organismo_comprador") or ""),
        "rut_organismo": str(institucion.get("rut") or ""),
        "unidad_compra": str(institucion.get("unidad_compra") or ""),
        "region_codigo": institucion.get("region"), "region": str(institucion.get("nombre_region") or ""),
        "moneda": str(montos.get("moneda") or "CLP"),
        "monto": montos.get("monto_disponible_clp") or montos.get("monto_disponible"),
        "fecha_publicacion": _datetime(fechas.get("fecha_publicacion")),
        "fecha_cierre": _datetime(fechas.get("fecha_cierre")),
        "fecha_ultimo_cambio": _datetime(fechas.get("fecha_ultimo_cambio")),
        "search_text": " ".join([codigo, nombre, descripcion, str(institucion.get("organismo_comprador") or "")]).lower(),
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
    initialize_database()
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
            query = query.filter(LicitacionActiva.activa.is_(True))
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
        update_columns = [key for key in rows[0] if key != "codigo"]
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
                       minimum_amount=None, maximum_amount=None, limit=50, offset=0):
    initialize_database()
    db = SessionLocal()
    try:
        results = []
        pattern = _keyword_pattern(keyword)
        if opportunity_type in ("all", "licitacion"):
            query = db.query(LicitacionActiva).filter(LicitacionActiva.activa.is_(True))
            if keyword: query = query.filter(LicitacionActiva.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(LicitacionActiva.region.ilike(f"%{region}%"))
            if organization: query = query.filter(LicitacionActiva.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(LicitacionActiva.estado.ilike(f"%{status}%"))
            results.extend(_licitacion_dict(row) for row in query.order_by(LicitacionActiva.fecha_cierre.asc()).limit(limit + offset).all())
        if opportunity_type in ("all", "compra_agil"):
            query = db.query(CompraAgil)
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
            if organization: query = query.filter(CompraAgil.organismo.ilike(f"%{organization}%"))
            if status:
                query = query.filter(CompraAgil.estado.ilike(f"%{status}%"))
            else:
                query = query.filter(CompraAgil.estado == "publicada")
            if minimum_amount is not None: query = query.filter(CompraAgil.monto >= minimum_amount)
            if maximum_amount is not None: query = query.filter(CompraAgil.monto <= maximum_amount)
            results.extend(_agile_dict(row) for row in query.order_by(CompraAgil.fecha_ultimo_cambio.desc()).limit(limit + offset).all())
        results.sort(key=lambda item: str(item.get("publish_date") or item.get("award_date") or ""), reverse=True)
        return results[offset:offset + limit]
    finally:
        db.close()


def count_opportunities(keyword="", opportunity_type="all", region="", organization="", status="",
                        minimum_amount=None, maximum_amount=None):
    initialize_database()
    db = SessionLocal()
    try:
        total = 0
        pattern = _keyword_pattern(keyword)
        if opportunity_type in ("all", "licitacion"):
            query = db.query(LicitacionActiva).filter(LicitacionActiva.activa.is_(True))
            if keyword: query = query.filter(LicitacionActiva.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(LicitacionActiva.region.ilike(f"%{region}%"))
            if organization: query = query.filter(LicitacionActiva.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(LicitacionActiva.estado.ilike(f"%{status}%"))
            total += query.count()
        if opportunity_type in ("all", "compra_agil"):
            query = db.query(CompraAgil)
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern, escape="\\"))
            if region: query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
            if organization: query = query.filter(CompraAgil.organismo.ilike(f"%{organization}%"))
            if status:
                query = query.filter(CompraAgil.estado.ilike(f"%{status}%"))
            else:
                query = query.filter(CompraAgil.estado == "publicada")
            if minimum_amount is not None: query = query.filter(CompraAgil.monto >= minimum_amount)
            if maximum_amount is not None: query = query.filter(CompraAgil.monto <= maximum_amount)
            total += query.count()
        return total
    finally:
        db.close()
