from datetime import datetime, timezone
from app.models.database import SessionLocal
from app.models.market_data import CompraAgil, Licitacion


def _datetime(value):
    if not value or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _licitacion_dict(row):
    detail = row.source_detail or {}
    comprador = detail.get("Comprador") or {}
    return {
        "id": f"licitacion:{row.id}", "source": "mercado_publico",
        "opportunity_type": "licitacion", "external_id": row.id,
        "title": row.nombre, "description": row.descripcion,
        "organization": row.organismo, "category": "", "amount": row.monto_licitacion,
        "currency": row.moneda, "publish_date": None,
        "award_date": row.fecha_adjudicacion, "closing_date": None,
        "status": "adjudicada", "region": comprador.get("RegionUnidad", ""),
        "url": detail.get("url") or detail.get("Url") or "",
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


def list_opportunities(keyword="", opportunity_type="all", region="", organization="", status="",
                       minimum_amount=None, maximum_amount=None, limit=50, offset=0):
    db = SessionLocal()
    try:
        results = []
        pattern = f"%{keyword}%"
        if opportunity_type in ("all", "licitacion"):
            query = db.query(Licitacion)
            if keyword: query = query.filter(Licitacion.search_text.ilike(pattern))
            if organization: query = query.filter(Licitacion.organismo.ilike(f"%{organization}%"))
            results.extend(_licitacion_dict(row) for row in query.order_by(Licitacion.updated_at.desc()).limit(limit + offset).all())
        if opportunity_type in ("all", "compra_agil"):
            query = db.query(CompraAgil)
            if keyword: query = query.filter(CompraAgil.search_text.ilike(pattern))
            if region: query = query.filter(CompraAgil.region.ilike(f"%{region}%"))
            if organization: query = query.filter(CompraAgil.organismo.ilike(f"%{organization}%"))
            if status: query = query.filter(CompraAgil.estado.ilike(f"%{status}%"))
            if minimum_amount is not None: query = query.filter(CompraAgil.monto >= minimum_amount)
            if maximum_amount is not None: query = query.filter(CompraAgil.monto <= maximum_amount)
            results.extend(_agile_dict(row) for row in query.order_by(CompraAgil.fecha_ultimo_cambio.desc()).limit(limit + offset).all())
        results.sort(key=lambda item: str(item.get("publish_date") or item.get("award_date") or ""), reverse=True)
        return results[offset:offset + limit]
    finally:
        db.close()
