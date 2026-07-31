from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
# Supabase entrega URLs postgresql://, pero este proyecto usa psycopg v3.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
API_TICKET = os.getenv("MERCADO_PUBLICO_TICKET", "")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CRON_SECRET = os.getenv("CRON_SECRET", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
CAPTCHA_SITE_KEY = os.getenv("CAPTCHA_SITE_KEY", "")
