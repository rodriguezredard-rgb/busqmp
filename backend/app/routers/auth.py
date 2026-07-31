import requests
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from app.core.config import SUPABASE_ANON_KEY, SUPABASE_URL

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RefreshPayload(BaseModel):
    refresh_token: str


class UpdatePayload(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6)


def supabase_request(path: str, method: str = "POST", payload: dict | None = None, authorization: str | None = None):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(503, "Supabase Auth no está configurado en el backend")
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    try:
        response = requests.request(method, f"{SUPABASE_URL}/auth/v1/{path}", headers=headers, json=payload, timeout=12)
    except requests.RequestException as exc:
        raise HTTPException(503, "No fue posible conectar con el servicio de autenticación") from exc
    data = response.json() if response.content else {}
    if not response.ok:
        detail = data.get("msg") or data.get("message") or data.get("error_description") or "No fue posible completar la solicitud"
        raise HTTPException(response.status_code, detail)
    return data


@router.post("/login")
def login(payload: Credentials):
    return supabase_request("token?grant_type=password", payload=payload.model_dump(mode="json"))


@router.post("/signup")
def signup(payload: Credentials):
    return supabase_request("signup", payload=payload.model_dump(mode="json"))


@router.post("/refresh")
def refresh(payload: RefreshPayload):
    return supabase_request("token?grant_type=refresh_token", payload=payload.model_dump())


@router.put("/credentials")
def update_credentials(payload: UpdatePayload, authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(401, "Debes iniciar sesión")
    return supabase_request("user", method="PUT", payload=payload.model_dump(exclude_none=True, mode="json"), authorization=authorization)


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    if authorization:
        supabase_request("logout", authorization=authorization)
