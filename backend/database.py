import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
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
    db_url = settings.DATABASE_URL

    if supabase_client and not _is_sqlite_url(db_url):
        try:
            engine = _create_sqlalchemy_engine(db_url)
            _test_engine(engine)
            print("Using Supabase/PostgreSQL database:", db_url)
            return engine
        except Exception as exc:
            print("Supabase/PostgreSQL connection failed:", str(exc))

    if not _is_sqlite_url(db_url):
        try:
            engine = _create_sqlalchemy_engine(db_url)
            _test_engine(engine)
            print("Using configured PostgreSQL database:", db_url)
            return engine
        except Exception as exc:
            print("PostgreSQL connection failed:", str(exc))

    fallback_url = DEFAULT_SQLITE_URL
    print("Falling back to local SQLite database:", fallback_url)
    return _create_sqlalchemy_engine(fallback_url)


engine = _resolve_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
