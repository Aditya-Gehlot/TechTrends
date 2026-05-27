from __future__ import annotations

import logging

from db.base import Base
from db.session import engine

# Import models so SQLAlchemy metadata is populated.
from db import models  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables are ready")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()

