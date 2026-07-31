from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from threading import Lock
from app.core.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Supabase Transaction Pooler (puerto 6543) no conserva el estado de
# prepared statements entre transacciones. Psycopg debe enviarlas sin preparar.
if DATABASE_URL.startswith("postgresql"):
    connect_args["prepare_threshold"] = None

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
_initialized = False
_initialize_lock = Lock()


def initialize_database() -> None:
    """Crea únicamente las tablas faltantes al primer acceso a datos."""
    global _initialized
    if _initialized:
        return
    with _initialize_lock:
        if _initialized:
            return
        Base.metadata.create_all(bind=engine)
        additions = {
            "licitaciones_activas": {"category_codes": "TEXT NOT NULL DEFAULT '[]'", "category_names": "TEXT NOT NULL DEFAULT '[]'"},
            "compras_agiles": {"category_codes": "TEXT NOT NULL DEFAULT '[]'", "category_names": "TEXT NOT NULL DEFAULT '[]'"},
            "busqmp_search_profiles": {"selected_categories": "TEXT NOT NULL DEFAULT '[]'", "owner_id": "VARCHAR(64)"},
        }
        inspector = inspect(engine)
        with engine.begin() as connection:
            for table_name, columns in additions.items():
                existing = {column["name"] for column in inspector.get_columns(table_name)}
                for column_name, definition in columns.items():
                    if column_name not in existing:
                        connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'))
        _initialized = True
