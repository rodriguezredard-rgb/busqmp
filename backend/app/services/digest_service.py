import json
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USERNAME
from app.models.opportunity import Opportunity
from app.models.search_profile import SearchProfile


def matching_opportunities(db: Session, profile: SearchProfile, limit: int = 100):
    query = db.query(Opportunity)
    included = json.loads(profile.include_keywords or "[]")
    excluded = json.loads(profile.exclude_keywords or "[]")
    if included:
        query = query.filter(or_(*[Opportunity.title.ilike(f"%{word}%") for word in included]))
    for word in excluded:
        query = query.filter(~Opportunity.title.ilike(f"%{word}%"))
    if profile.opportunity_type != "all":
        query = query.filter(Opportunity.opportunity_type == profile.opportunity_type)
    if profile.region:
        query = query.filter(Opportunity.region.ilike(f"%{profile.region}%"))
    if profile.organization:
        query = query.filter(Opportunity.organization.ilike(f"%{profile.organization}%"))
    if profile.status:
        query = query.filter(Opportunity.status.ilike(f"%{profile.status}%"))
    if profile.minimum_amount is not None:
        query = query.filter(Opportunity.amount >= profile.minimum_amount)
    if profile.maximum_amount is not None:
        query = query.filter(Opportunity.amount <= profile.maximum_amount)
    yesterday = date.today() - timedelta(days=1)
    query = query.filter(or_(Opportunity.publish_date >= yesterday, Opportunity.publish_date.is_(None)))
    return query.order_by(Opportunity.publish_date.desc(), Opportunity.id.desc()).limit(limit).all()


def send_digest(profile: SearchProfile, rows: list[Opportunity]):
    if not SMTP_HOST or not SMTP_FROM:
        raise RuntimeError("El servicio SMTP no está configurado")
    lines = [f"Resumen diario: {profile.name}", ""]
    if not rows:
        lines.append("Hoy no se encontraron oportunidades nuevas que coincidan con tu búsqueda.")
    for row in rows:
        lines.extend([f"• {row.title}", f"  {row.organization or 'Sin organismo'}", f"  {row.url or row.external_id}", ""])
    message = EmailMessage()
    message["Subject"] = f"{len(rows)} oportunidades — {profile.name}"
    message["From"] = SMTP_FROM
    message["To"] = profile.recipient_email
    message.set_content("\n".join(lines))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        if SMTP_USERNAME:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def run_due_digests(db: Session) -> list[dict]:
    results = []
    for profile in db.query(SearchProfile).filter(SearchProfile.enabled.is_(True)).all():
        try:
            now = datetime.now(ZoneInfo(profile.timezone))
        except ZoneInfoNotFoundError:
            results.append({"profile_id": profile.id, "status": "invalid_timezone"})
            continue
        if profile.last_sent_on == now.date() or now.time().replace(tzinfo=None) < profile.delivery_time:
            continue
        rows = matching_opportunities(db, profile)
        try:
            send_digest(profile, rows)
            profile.last_sent_on = now.date()
            db.commit()
            results.append({"profile_id": profile.id, "status": "sent", "count": len(rows)})
        except Exception as exc:
            db.rollback()
            results.append({"profile_id": profile.id, "status": "error", "detail": str(exc)})
    return results
