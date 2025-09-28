"""Database engine helpers using SQLModel."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager

from sqlmodel import Session, SQLModel, create_engine

from warehouse_service.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database.url,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
        )
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Session:
    engine = get_engine()
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - re-raised upstream
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_session_scope():
    """Placeholder for future async session support."""

    raise NotImplementedError("Async session scope will be implemented in a future iteration")
