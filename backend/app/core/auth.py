import requests
from fastapi import Header, HTTPException
from app.core.config import SUPABASE_ANON_KEY, SUPABASE_URL


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(503, "La autenticación no está configurada")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Debes iniciar sesión")
    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": authorization},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise HTTPException(503, "No fue posible validar la sesión") from exc
    if response.status_code != 200:
        raise HTTPException(401, "La sesión expiró o no es válida")
    return response.json()
