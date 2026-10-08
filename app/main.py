from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.api.v1 import router as v1
from app.core.config import get_settings
from app.middleware.latency import LatencyHeaderMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Redis / Kafka clients will be opened and closed here.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

    app.add_middleware(LatencyHeaderMiddleware)

    app.include_router(health.router)
    app.include_router(v1.router, prefix="/api/v1")
    return app


app = create_app()
