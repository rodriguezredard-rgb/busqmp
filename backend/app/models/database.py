from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Supabase Transaction Pooler (puerto 6543) no conserva el estado de
# prepared statements entre transacciones. Psycopg debe enviarlas sin preparar.
if DATABASE_URL.startswith("postgresql"):
    connect_args["prepare_threshold"] = None

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def initialize_database() -> None:
    """Crea únicamente las tablas faltantes al primer acceso a datos."""
    Base.metadata.create_all(bind=engine)
