import json
from datetime import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.search_profile import SearchProfile
from app.core.auth import current_user

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfilePayload(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    industry: str = ""
    include_keywords: list[str] = []
    exclude_keywords: list[str] = []
    selected_categories: list[str] = []
    opportunity_type: str = "all"
    region: str = ""
    organization: str = ""
    status: str = ""
    minimum_amount: int | None = None
    maximum_amount: int | None = None
    recipient_email: EmailStr
    delivery_time: time
    timezone: str = "America/Santiago"
    enabled: bool = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize(row: SearchProfile) -> dict:
    return {
        "id": row.id, "name": row.name, "industry": row.industry,
        "include_keywords": json.loads(row.include_keywords or "[]"),
        "exclude_keywords": json.loads(row.exclude_keywords or "[]"),
        "selected_categories": json.loads(row.selected_categories or "[]"),
        "opportunity_type": row.opportunity_type, "region": row.region,
        "organization": row.organization, "status": row.status,
        "minimum_amount": row.minimum_amount, "maximum_amount": row.maximum_amount,
        "recipient_email": row.recipient_email,
        "delivery_time": row.delivery_time.strftime("%H:%M"), "timezone": row.timezone,
        "enabled": row.enabled, "last_sent_on": row.last_sent_on,
    }


def values(payload: ProfilePayload) -> dict:
    data = payload.model_dump()
    data["include_keywords"] = json.dumps([x.strip() for x in payload.include_keywords if x.strip()], ensure_ascii=False)
    data["exclude_keywords"] = json.dumps([x.strip() for x in payload.exclude_keywords if x.strip()], ensure_ascii=False)
    data["selected_categories"] = json.dumps([x.strip() for x in payload.selected_categories if x.strip()], ensure_ascii=False)
    return data


@router.get("")
def list_profiles(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    # Conserva las búsquedas creadas antes del login cuando el destinatario
    # coincide con el correo verificado de la cuenta que ingresa.
    email = (user.get("email") or "").lower()
    if email:
        legacy_rows = db.query(SearchProfile).filter(
            SearchProfile.owner_id.is_(None),
            SearchProfile.recipient_email.ilike(email),
        ).all()
        if legacy_rows:
            for row in legacy_rows:
                row.owner_id = user["id"]
            db.commit()
    return [serialize(row) for row in db.query(SearchProfile).filter(SearchProfile.owner_id == user["id"]).order_by(SearchProfile.name).all()]


@router.post("", status_code=201)
def create_profile(payload: ProfilePayload, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    row = SearchProfile(owner_id=user["id"], **values(payload))
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.put("/{profile_id}")
def update_profile(profile_id: int, payload: ProfilePayload, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(SearchProfile).filter(SearchProfile.id == profile_id, SearchProfile.owner_id == user["id"]).first()
    if not row:
        raise HTTPException(404, "Perfil no encontrado")
    for key, value in values(payload).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(SearchProfile).filter(SearchProfile.id == profile_id, SearchProfile.owner_id == user["id"]).first()
    if not row:
        raise HTTPException(404, "Perfil no encontrado")
    db.delete(row)
    db.commit()
