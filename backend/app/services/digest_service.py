import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session
from app.core.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USERNAME
from app.models.search_profile import SearchProfile
from app.services.opportunity_service import list_opportunities


def matching_opportunities(profile: SearchProfile, limit: int = 100):
    included = json.loads(profile.include_keywords or "[]") or [""]
    excluded = [word.lower() for word in json.loads(profile.exclude_keywords or "[]")]
    selected_categories = set(json.loads(profile.selected_categories or "[]"))
    rows = []
    for keyword in included:
        rows.extend(list_opportunities(
            keyword=keyword, opportunity_type=profile.opportunity_type,
            region=profile.region, organization=profile.organization, status=profile.status,
            minimum_amount=profile.minimum_amount, maximum_amount=profile.maximum_amount,
            limit=limit,
        ))
    unique = {row["id"]: row for row in rows}
    return [row for row in unique.values()
            if (not selected_categories or selected_categories.intersection(row.get("category_codes") or []))
            and not any(word in f"{row['title']} {row.get('description', '')}".lower() for word in excluded)][:limit]


def send_digest(profile: SearchProfile, rows: list[dict]):
    if not SMTP_HOST or not SMTP_FROM:
        raise RuntimeError("El servicio SMTP no está configurado")
    lines = [f"Resumen diario: {profile.name}", ""]
    if not rows:
        lines.append("Hoy no se encontraron oportunidades que coincidan con tu búsqueda.")
    for row in rows:
        lines.extend([f"• {row['title']}", f"  {row.get('organization') or 'Sin organismo'}",
                      f"  {row.get('url') or row['external_id']}", ""])
    message = EmailMessage()
    message["Subject"] = f"{len(rows)} oportunidades — {profile.name}"
    message["From"], message["To"] = SMTP_FROM, profile.recipient_email
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
        rows = matching_opportunities(profile)
        try:
            send_digest(profile, rows)
            profile.last_sent_on = now.date()
            db.commit()
            results.append({"profile_id": profile.id, "status": "sent", "count": len(rows)})
        except Exception as exc:
            db.rollback()
            results.append({"profile_id": profile.id, "status": "error", "detail": str(exc)})
    return results
