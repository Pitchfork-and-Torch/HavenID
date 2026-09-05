from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import Settings, _API_DIR, get_settings


def _resolve_database_url(url: str) -> str:
    """Pin relative sqlite files to apps/api so cwd cannot hide the owner DB."""
    marker = ":///"
    if not url.startswith("sqlite") or marker not in url:
        return url
    prefix, rest = url.split(marker, 1)
    if rest.startswith("./") or (rest and not rest.startswith("/") and ":" not in rest[:2]):
        abs_path = (_API_DIR / rest.lstrip("./")).resolve()
        return f"{prefix}:///{abs_path.as_posix()}"
    return url


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def configure_engine(settings: Settings | None = None) -> None:
    global engine, SessionLocal
    settings = settings or get_settings()
    connect_args = {}
    url = _resolve_database_url(settings.database_url)
    kwargs: dict = {"echo": False}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        kwargs["poolclass"] = StaticPool
    engine = create_async_engine(url, connect_args=connect_args, **kwargs)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(*, reset: bool = False) -> None:
    if engine is None:
        configure_engine()
    from app import models  # noqa: F401

    assert engine is not None
    async with engine.begin() as conn:
        if reset:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        configure_engine()
    assert SessionLocal is not None
    async with SessionLocal() as session:
        yield session
