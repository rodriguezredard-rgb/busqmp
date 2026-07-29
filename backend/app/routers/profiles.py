import json
from datetime import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, initialize_database
from app.models.search_profile import SearchProfile

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfilePayload(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    industry: str = ""
    include_keywords: list[str] = []
    exclude_keywords: list[str] = []
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
    initialize_database()
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
    return data


@router.get("")
def list_profiles(db: Session = Depends(get_db)):
    return [serialize(row) for row in db.query(SearchProfile).order_by(SearchProfile.name).all()]


@router.post("", status_code=201)
def create_profile(payload: ProfilePayload, db: Session = Depends(get_db)):
    row = SearchProfile(**values(payload))
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.put("/{profile_id}")
def update_profile(profile_id: int, payload: ProfilePayload, db: Session = Depends(get_db)):
    row = db.get(SearchProfile, profile_id)
    if not row:
        raise HTTPException(404, "Perfil no encontrado")
    for key, value in values(payload).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.get(SearchProfile, profile_id)
    if not row:
        raise HTTPException(404, "Perfil no encontrado")
    db.delete(row)
    db.commit()
