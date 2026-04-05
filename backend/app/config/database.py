from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def create_schemas() -> None:
    """Create Postgres schemas if they do not exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS product"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marketing"))
        conn.commit()


shared_metadata = MetaData()


class ProductBase(DeclarativeBase):
    metadata = shared_metadata


class MarketingBase(DeclarativeBase):
    metadata = shared_metadata
