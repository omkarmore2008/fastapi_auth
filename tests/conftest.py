"""Pytest fixtures for auth service tests."""

from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.models import auth  # noqa: F401


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated in-memory DB session per test.

    Args:
        None
    Returns:
        AsyncGenerator[AsyncSession, None]: Async SQLAlchemy session fixture.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
async def redis_client():
    """Provide isolated fake Redis client per test.

    Args:
        None
    Returns:
        FakeRedis: Async fake redis client.
    """
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()
