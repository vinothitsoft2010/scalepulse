from fastapi import APIRouter, Request
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from app.core.database import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "ScalePulse Edge Gateway"}


@router.get("/ready")
async def readiness_check(request: Request) -> JSONResponse:
    engine = request.app.state.database_engine
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "not_configured"},
        )

    try:
        await check_database(engine)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )

    if request.app.state.settings.rate_limit_enabled:
        pepper = request.app.state.settings.api_key_pepper
        if pepper is None or not pepper.get_secret_value():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "rate_limiter": "not_configured"},
            )
        redis_client = request.app.state.redis_client
        if redis_client is None:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "redis": "not_configured"},
            )
        try:
            await redis_client.ping()
        except RedisError:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "redis": "unavailable"},
            )

    return JSONResponse(
        content={
            "status": "ready",
            "database": "healthy",
            "redis": "healthy" if request.app.state.settings.rate_limit_enabled else "disabled",
        }
    )
