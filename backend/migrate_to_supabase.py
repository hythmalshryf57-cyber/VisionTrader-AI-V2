import os
from pathlib import Path
from datetime import datetime
from config import settings

try:
    from supabase import create_client
except ImportError:
    create_client = None

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import models

BASE_DIR = Path(__file__).resolve().parent
SQLITE_URL = f"sqlite:///{BASE_DIR / 'visiontrader.db'}"


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row_to_dict(row):
    return {
        column.name: _serialize_value(getattr(row, column.name))
        for column in row.__table__.columns
        if getattr(row, column.name) is not None
    }


def _create_sqlite_session():
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _create_supabase_engine():
    engine = create_engine(settings.DATABASE_URL, future=True)
    return engine


def _create_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def _migrate_table(client, table_name, rows):
    if not rows:
        print(f"Skipping {table_name}: no rows to migrate")
        return

    payload = [_row_to_dict(row) for row in rows]
    try:
        response = client.table(table_name).upsert(payload, on_conflict="id").execute()
    except AttributeError:
        response = client.table(table_name).insert(payload).execute()

    if response.error:
        print(f"Warning: migration for {table_name} returned error:", response.error)
    else:
        print(f"Migrated {len(payload)} rows into {table_name}")


def _reset_sequences(engine, tables):
    with engine.connect() as conn:
        for table in tables:
            stmt = text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1), true) FROM {table};"
            )
            conn.execute(stmt)
        conn.commit()


def main():
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
        return

    if create_client is None:
        print("Supabase client library is not installed. Run pip install supabase or install requirements.")
        return

    if not settings.DATABASE_URL or settings.DATABASE_URL.startswith("sqlite"):
        print("DATABASE_URL must point to your Supabase PostgreSQL database URL for migration.")
        return

    supabase_client = _create_supabase_client()
    if supabase_client is None:
        print("Could not create Supabase client. Check SUPABASE_URL and SUPABASE_KEY.")
        return

    supabase_engine = _create_supabase_engine()

    print("Creating tables in Supabase if they do not exist...")
    models.Base.metadata.create_all(bind=supabase_engine)

    sqlite_session = _create_sqlite_session()

    ordered_models = [
        models.User,
        models.InviteCode,
        models.UserPreferences,
        models.UserDevice,
        models.UserActivityMaster,
        models.SecurityLog,
        models.Analysis,
        models.Alert,
        models.JournalEntry,
        models.StrategyPerformance,
        models.WeeklyReport,
        models.PsychologyLog,
        models.ShadowTrade,
    ]

    for model in ordered_models:
        rows = sqlite_session.query(model).all()
        _migrate_table(supabase_client, model.__tablename__, rows)

    _reset_sequences(
        supabase_engine,
        [model.__tablename__ for model in ordered_models],
    )

    print("Migration complete. Verify data in Supabase and then restart the application.")


if __name__ == "__main__":
    main()
