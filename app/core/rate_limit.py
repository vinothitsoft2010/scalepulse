from dataclasses import dataclass
from secrets import token_hex

from redis.asyncio import Redis

API_KEY_CACHE_TTL_SECONDS = 10
INVALID_API_KEY_CACHE_TTL_SECONDS = 3

SLIDING_WINDOW_SCRIPT = """
local metadata_json = redis.call('GET', KEYS[1])
if not metadata_json then
    return {-2}
end

local metadata = cjson.decode(metadata_json)
if metadata.invalid then
    return {-1}
end
if not metadata.enabled then
    return {-3}
end

local limit = tonumber(metadata.request_limit)
local window_ms = tonumber(metadata.window_ms)
local clock = redis.call('TIME')
local now_ms = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
if metadata.expires_at_ms and metadata.expires_at_ms ~= cjson.null
    and now_ms >= tonumber(metadata.expires_at_ms) then
    return {-1}
end
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now_ms - window_ms)

local count = redis.call('ZCARD', KEYS[2])
local oldest = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
if count >= limit then
    local reset_at = tonumber(oldest[2]) + window_ms
    return {0, limit, 0, math.max(1, reset_at - now_ms)}
end

redis.call('ZADD', KEYS[2], now_ms, ARGV[1])
redis.call('PEXPIRE', KEYS[2], window_ms + 1000)
count = count + 1
oldest = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
local reset_at = tonumber(oldest[2]) + window_ms
return {1, limit, limit - count, math.max(0, reset_at - now_ms)}
"""


@dataclass(frozen=True)
class RateLimitDecision:
    status: int
    limit: int = 0
    remaining: int = 0
    reset_after_ms: int = 0


class RedisSlidingWindowLimiter:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._script = redis.register_script(SLIDING_WINDOW_SCRIPT)

    @staticmethod
    def api_key_cache_key(digest_hex: str) -> str:
        return f"scalepulse:api-key:{{{digest_hex}}}"

    @staticmethod
    def counter_key(digest_hex: str) -> str:
        return f"scalepulse:rate:{{{digest_hex}}}"

    async def check(self, digest_hex: str) -> RateLimitDecision:
        result = await self._script(
            keys=[self.api_key_cache_key(digest_hex), self.counter_key(digest_hex)],
            args=[token_hex(16)],
        )
        values = [int(value) for value in result]
        if values[0] < 0:
            return RateLimitDecision(status=values[0])
        return RateLimitDecision(
            status=values[0],
            limit=values[1],
            remaining=values[2],
            reset_after_ms=values[3],
        )
