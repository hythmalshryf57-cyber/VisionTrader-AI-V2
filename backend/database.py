import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

try:
    from .config import settings
except ImportError:
    from config import settings

try:
    from .supabase_client import supabase_client
except ImportError:
    from supabase_client import supabase_client

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'visiontrader.db'}"


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _create_sqlalchemy_engine(url: str):
    connect_args = {"check_same_thread": False} if _is_sqlite_url(url) else {}
    return create_engine(url, future=True, connect_args=connect_args)


def _test_engine(engine):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()


def _resolve_engine():
    db_url = (settings.DATABASE_URL or os.getenv("DATABASE_URL") or "").strip()

    if not db_url:
        print("Using local persistent SQLite database:", DEFAULT_SQLITE_URL)
        return _create_sqlalchemy_engine(DEFAULT_SQLITE_URL)

    if _is_sqlite_url(db_url):
        print("Using configured SQLite database:", db_url)
        return _create_sqlalchemy_engine(db_url)

    try:
        engine = _create_sqlalchemy_engine(db_url)
        _test_engine(engine)
        print("Using configured PostgreSQL database:", db_url)
        return engine
    except Exception as exc:
        print("PostgreSQL connection failed; falling back to SQLite database:", str(exc))
        return _create_sqlalchemy_engine(DEFAULT_SQLITE_URL)



engine = _resolve_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_tables(base):
    try:
        base.metadata.create_all(bind=engine)
        print("Database tables created or verified.")
    except Exception as exc:
        print(f"Database table creation failed: {exc}")
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
