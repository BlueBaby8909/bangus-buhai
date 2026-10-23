"""Rebuild-only configuration and bounded SQLAlchemy connection pooling."""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlmodel import Session

LOCAL_ENV = Path(__file__).resolve().parents[2] / "database" / ".env"


def setting(name: str) -> str:
    if name in os.environ:
        return os.environ[name]
    if LOCAL_ENV.is_file():
        for line in LOCAL_ENV.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key == name:
                return value
    raise RuntimeError(f"Missing {name}; configure the rebuild database explicitly")


def database_url(*, test: bool = False):
    url = make_url(setting("BB_TEST_DATABASE_URL" if test else "BB_DATABASE_URL"))
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise RuntimeError("Expected an explicit postgresql+psycopg database URL")
    if test and url.database != "bangus_buhai_rebuild_test":
        raise RuntimeError("Tests require the dedicated bangus_buhai_rebuild_test database")
    return url


def make_engine(*, test: bool = False) -> Engine:
    return create_engine(
        database_url(test=test), pool_size=5, max_overflow=5,
        pool_timeout=10, pool_pre_ping=True, hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


@contextmanager
def transaction(engine: Engine):
    """One transaction/session per operation; caller uses this as a context manager."""
    with Session(engine) as session, session.begin():
        yield session
