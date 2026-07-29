from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.database import SessionLocal
from app.models.market_data import CompraAgil, LicitacionActiva


def _datetime(value):
    if not value or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _licitacion_dict(row):
    return {
        "id": f"licitacion:{row.codigo}", "source": "mercado_publico",
        "opportunity_type": "licitacion", "external_id": row.codigo,
        "title": row.nombre, "description": row.descripcion,
        "organization": row.organismo, "category": "", "amount": None,
        "currency": "CLP", "publish_date": row.fecha_publicacion,
        "award_date": None, "closing_date": row.fecha_cierre,
        "status": row.estado, "region": row.region,
        "url": "",
    }


def _agile_dict(row):
    return {
        "id": f"compra_agil:{row.codigo}", "source": "compras_agiles",
        "opportunity_type": "compra_agil", "external_id": row.codigo,
        "title": row.nombre, "description": row.descripcion,
        "organization": row.organismo, "category": "", "amount": float(row.monto) if row.monto is not None else None,
        "currency": row.moneda, "publish_date": row.fecha_publicacion,
        "award_date": None, "closing_date": row.fecha_cierre,
        "status": row.estado, "region": row.region,
        "url": f"https://api2.mercadopublico.cl/v2/compra-agil/{row.codigo}",
    }


def save_compra_agil(data: dict) -> None:
    codigo = str(data.get("codigo") or "").strip()
    if not codigo:
        return
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
    db = SessionLocal()
    try:
        row = db.get(CompraAgil, codigo)
        if row:
            for key, value in values.items(): setattr(row, key, value)
        else:
            db.add(CompraAgil(codigo=codigo, **values))
        db.commit()
    finally:
        db.close()


def sync_active_licitaciones(items: list[dict]) -> int:
    """Reemplaza lógicamente el inventario activo sin borrar su historial."""
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
    db = SessionLocal()
    try:
        results = []
        pattern = f"%{keyword}%"
        if opportunity_type in ("all", "licitacion"):
            query = db.query(LicitacionActiva).filter(LicitacionActiva.activa.is_(True))
            if keyword: query = query.filter(LicitacionActiva.search_text.ilike(pattern))
            if region: query = query.filter(LicitacionActiva.region.ilike(f"%{region}%"))
            if organization: query = query.filter(LicitacionActiva.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(LicitacionActiva.estado.ilike(f"%{status}%"))
            results.extend(_licitacion_dict(row) for row in query.order_by(LicitacionActiva.fecha_cierre.asc()).limit(limit + offset).all())
        if opportunity_type in ("all", "compra_agil"):
            query = db.query(CompraAgil)
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern))
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
