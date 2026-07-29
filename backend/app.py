"""Punto de entrada ASGI para desplegar el backend como Vercel Function."""
from app.main import app

__all__ = ["app"]
