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
    db_url = (settings.DATABASE_URL or "").strip()

    # If DATABASE_URL is empty, allow explicit development fallback only.
    if not db_url:
        env = os.getenv("ENV", os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production"))).lower()
        if env in ("development", "dev", "local", "testing"):
            fallback_url = DEFAULT_SQLITE_URL
            print("No DATABASE_URL set. Using local SQLite database for development:", fallback_url)
            return _create_sqlalchemy_engine(fallback_url)
        raise RuntimeError(
            "DATABASE_URL is not configured. In production a PostgreSQL DATABASE_URL must be provided."
        )

    # If a sqlite URL is explicitly provided, use it (development).
    if _is_sqlite_url(db_url):
        print("Using local SQLite database:", db_url)
        return _create_sqlalchemy_engine(db_url)

    # At this point we expect a PostgreSQL-style URL. Try Supabase/Postgres first if available.
    if supabase_client and not _is_sqlite_url(db_url):
        try:
            engine = _create_sqlalchemy_engine(db_url)
            _test_engine(engine)
            print("Using Supabase/PostgreSQL database:", db_url)
            return engine
        except Exception as exc:
            env = os.getenv("ENV", os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production"))).lower()
            if env in ("development", "dev", "local", "testing"):
                print("Supabase/PostgreSQL connection failed; falling back to local SQLite for development:", str(exc))
                return _create_sqlalchemy_engine(DEFAULT_SQLITE_URL)
            raise RuntimeError(f"Supabase/PostgreSQL connection failed in production: {exc}")

    # Try connecting to the configured PostgreSQL database directly.
    try:
        engine = _create_sqlalchemy_engine(db_url)
        _test_engine(engine)
        print("Using configured PostgreSQL database:", db_url)
        return engine
    except Exception as exc:
        env = os.getenv("ENV", os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production"))).lower()
        if env in ("development", "dev", "local", "testing"):
            print("PostgreSQL connection failed; falling back to local SQLite for development:", str(exc))
            return _create_sqlalchemy_engine(DEFAULT_SQLITE_URL)
        # In production do not silently fallback — raise a clear error.
        raise RuntimeError(
            f"PostgreSQL connection failed in production: {exc}. Please verify DATABASE_URL and database availability."
        )


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
