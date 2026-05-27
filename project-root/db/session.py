from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings


def db_configured() -> bool:
    return bool(getattr(settings, "DATABASE_URL", "").strip())


def persistence_enabled() -> bool:
    return bool(getattr(settings, "ENABLE_DB_PERSISTENCE", False) and db_configured())


engine = create_engine(
    settings.DATABASE_URL,
    echo=getattr(settings, "DB_ECHO", False),
    pool_pre_ping=True,
    future=True,
) if db_configured() else None

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True) if engine else None


@contextmanager
def session_scope() -> Iterator[Session]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

