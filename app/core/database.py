from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_database_engine(database_url: str | None) -> AsyncEngine | None:
    if database_url is None:
        return None
    return create_async_engine(database_url, pool_pre_ping=True)


async def check_database(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def create_redis_client(redis_url: str | None) -> Redis | None:
    if redis_url is None:
        return None
    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
        health_check_interval=30,
    )
