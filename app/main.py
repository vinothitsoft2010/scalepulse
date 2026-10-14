from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api import health
from app.api.v1 import admin
from app.api.v1 import router as v1
from app.core.config import Settings, get_settings
from app.core.database import create_database_engine, create_redis_client
from app.core.rate_limit import RedisSlidingWindowLimiter
from app.middleware.latency import LatencyHeaderMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine: AsyncEngine | None = create_database_engine(settings.database_url)
        redis_client: Redis | None = create_redis_client(settings.redis_url)
        app.state.database_engine = engine
        app.state.redis_client = redis_client
        app.state.rate_limiter = (
            RedisSlidingWindowLimiter(redis_client) if redis_client is not None else None
        )
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            if redis_client is not None:
                await redis_client.aclose()

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(LatencyHeaderMiddleware)

    app.include_router(health.router)
    app.include_router(v1.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    return app


app = create_app()
