"""Database and Redis session clients."""

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_db_session() -> AsyncSession:
    """Yield one database session per request.

    Args:
        None
    Returns:
        AsyncSession: SQLAlchemy async session.
    """
    async with AsyncSessionFactory() as session:
        yield session


async def get_redis() -> Redis:
    """Yield redis client dependency.

    Args:
        None
    Returns:
        Redis: Async Redis client.
    """
    return redis_client
