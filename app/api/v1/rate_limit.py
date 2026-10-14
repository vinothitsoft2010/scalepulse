import hashlib
import hmac
import json
from math import ceil
from typing import Annotated

from fastapi import Header, HTTPException, Request, Response
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.core.rate_limit import (
    API_KEY_CACHE_TTL_SECONDS,
    INVALID_API_KEY_CACHE_TTL_SECONDS,
    RedisSlidingWindowLimiter,
)
from app.repositories import admin as repository


async def enforce_rate_limit(
    request: Request,
    response: Response,
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    settings = request.app.state.settings
    if not settings.rate_limit_enabled:
        return
    if api_key is None or not api_key.startswith("sp_live_") or len(api_key) > 128:
        raise HTTPException(status_code=401, detail="invalid_api_key")

    pepper = settings.api_key_pepper
    redis_client = request.app.state.redis_client
    limiter: RedisSlidingWindowLimiter | None = request.app.state.rate_limiter
    if pepper is None or not pepper.get_secret_value() or redis_client is None or limiter is None:
        raise HTTPException(status_code=503, detail="rate_limiter_not_configured")

    digest = hmac.new(pepper.get_secret_value().encode(), api_key.encode(), hashlib.sha256).digest()
    digest_hex = digest.hex()
    cache_key = limiter.api_key_cache_key(digest_hex)
    try:
        decision = await limiter.check(digest_hex)
        if decision.status == -2:
            engine = request.app.state.database_engine
            if engine is None:
                raise HTTPException(status_code=503, detail="database_not_configured")
            metadata = await repository.get_rate_limit_metadata(engine, digest)
            if metadata is None:
                await redis_client.set(
                    cache_key,
                    json.dumps({"invalid": True}),
                    ex=INVALID_API_KEY_CACHE_TTL_SECONDS,
                )
                raise HTTPException(status_code=401, detail="invalid_api_key")
            await redis_client.set(
                cache_key,
                json.dumps(metadata),
                ex=API_KEY_CACHE_TTL_SECONDS,
            )
            decision = await limiter.check(digest_hex)
    except HTTPException:
        raise
    except (RedisError, SQLAlchemyError) as error:
        raise HTTPException(status_code=503, detail="rate_limiter_unavailable") from error

    if decision.status == -1:
        raise HTTPException(status_code=401, detail="invalid_api_key")
    if decision.status == -3:
        raise HTTPException(status_code=403, detail="rate_limit_policy_disabled")
    if decision.status < 0:
        raise HTTPException(status_code=503, detail="rate_limiter_unavailable")

    reset_after_seconds = ceil(decision.reset_after_ms / 1000)
    headers = {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(reset_after_seconds),
    }
    if decision.status == 0:
        headers["Retry-After"] = str(max(1, reset_after_seconds))
        raise HTTPException(
            status_code=429,
            detail={"code": "rate_limit_exceeded"},
            headers=headers,
        )

    response.headers.update(headers)
