import asyncio
import json
import os
import uuid

from redis.asyncio import Redis

from app.core.rate_limit import RedisSlidingWindowLimiter


def test_sliding_window_is_atomic_under_concurrency() -> None:
    async def exercise() -> None:
        redis_url = os.getenv("SCALEPULSE_REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        digest_hex = uuid.uuid4().hex
        limiter = RedisSlidingWindowLimiter(redis)
        metadata_key = limiter.api_key_cache_key(digest_hex)
        counter_key = limiter.counter_key(digest_hex)
        try:
            await redis.set(
                metadata_key,
                json.dumps(
                    {
                        "api_key_id": str(uuid.uuid4()),
                        "policy_id": str(uuid.uuid4()),
                        "request_limit": 10,
                        "window_ms": 500,
                        "enabled": True,
                        "expires_at_ms": None,
                    }
                ),
                ex=10,
            )
            decisions = await asyncio.gather(*(limiter.check(digest_hex) for _ in range(100)))
            assert sum(decision.status == 1 for decision in decisions) == 10
            assert sum(decision.status == 0 for decision in decisions) == 90

            await asyncio.sleep(0.55)
            after_window = await limiter.check(digest_hex)
            assert after_window.status == 1
        finally:
            await redis.delete(metadata_key, counter_key)
            await redis.aclose()

    asyncio.run(exercise())
