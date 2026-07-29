import json
from typing import List, Dict
from sqlalchemy import or_
from app.models.database import SessionLocal
from app.models.opportunity import Opportunity


def save_opportunity(data: dict) -> None:
    db = SessionLocal()
    try:
        external_id = str(data.get("external_id", "")).strip()
        if not external_id:
            return
        record = db.query(Opportunity).filter_by(
            source=data.get("source", "mercado_publico"), external_id=external_id
        ).one_or_none()
        values = dict(
            source=data.get("source", "mercado_publico"),
            opportunity_type=data.get("opportunity_type", "licitacion"),
            external_id=external_id,
            title=data.get("title", ""),
            organization=data.get("organization"),
            category=data.get("category"),
            amount=data.get("amount"),
            currency=data.get("currency"),
            publish_date=data.get("publish_date"),
            award_date=data.get("award_date"),
            closing_date=data.get("closing_date"),
            status=data.get("status"),
            region=data.get("region"),
            tags=data.get("tags"),
            url=data.get("url"),
            notes=data.get("notes"),
            details=json.dumps(data.get("details"), ensure_ascii=False) if isinstance(data.get("details"), (dict, list)) else data.get("details"),
        )
        if record:
            for key, value in values.items():
                setattr(record, key, value)
        else:
            db.add(Opportunity(**values))
        db.commit()
    finally:
        db.close()


def list_opportunities(
    keyword: str = "", opportunity_type: str = "all", region: str = "",
    organization: str = "", status: str = "", minimum_amount: float | None = None,
    maximum_amount: float | None = None, limit: int = 50, offset: int = 0,
) -> List[Dict]:
    db = SessionLocal()
    try:
        query = db.query(Opportunity)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(or_(Opportunity.title.ilike(pattern), Opportunity.category.ilike(pattern), Opportunity.tags.ilike(pattern)))
        if opportunity_type and opportunity_type != "all":
            query = query.filter(Opportunity.opportunity_type == opportunity_type)
        if region:
            query = query.filter(Opportunity.region.ilike(f"%{region}%"))
        if organization:
            query = query.filter(Opportunity.organization.ilike(f"%{organization}%"))
        if status:
            query = query.filter(Opportunity.status.ilike(f"%{status}%"))
        if minimum_amount is not None:
            query = query.filter(Opportunity.amount >= minimum_amount)
        if maximum_amount is not None:
            query = query.filter(Opportunity.amount <= maximum_amount)
        rows = query.order_by(Opportunity.publish_date.desc(), Opportunity.id.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": row.id,
                "source": row.source,
                "opportunity_type": row.opportunity_type,
                "external_id": row.external_id,
                "title": row.title,
                "organization": row.organization,
                "category": row.category,
                "amount": row.amount,
                "currency": row.currency,
                "publish_date": row.publish_date,
                "award_date": row.award_date,
                "closing_date": row.closing_date,
                "status": row.status,
                "region": row.region,
                "tags": row.tags,
                "url": row.url,
                "notes": row.notes,
                "details": row.details,
            }
            for row in rows
        ]
    finally:
        db.close()
