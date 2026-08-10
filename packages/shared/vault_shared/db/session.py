from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from vault_shared.settings import get_settings

# The declarative base every future ORM model (Phase 2 onward) inherits from.
# Kept here, not per-model, so Alembic's autogenerate has a single metadata
# object to diff against regardless of which phase adds which table.
Base = declarative_base()


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """A single-use session generator — used as a FastAPI dependency in
    apps/backend (one session per request); apps/worker uses
    `get_session_factory()` directly instead (one session per job)."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
