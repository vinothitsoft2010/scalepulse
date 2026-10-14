# Redis Rate-Limit Design

## Request path

1. The route requires an `X-API-Key` header.
2. The gateway computes an HMAC-SHA-256 digest with `SCALEPULSE_API_KEY_PEPPER`; the raw secret is never used as a database or Redis key.
3. Redis Lua reads cached policy metadata and atomically prunes old sorted-set entries, checks the allowance, and records an accepted request.
4. A cold metadata cache loads the key and policy from PostgreSQL, then caches the result briefly in Redis.
5. Missing/invalid keys return 401, disabled policies return 403, exhausted quotas return 429, and unavailable required infrastructure returns 503.

## Why a sorted set and Lua?

Each allowed request is a sorted-set member scored by Redis server time. The script performs prune, count, and conditional insert as one atomic operation. That prevents two workers from both spending the same final request. Denied requests are not added, so the set is bounded by the configured allowance for the active window.

The exact log is easy to reason about at the N/N+1 boundary, but each request requires sorted-set work and memory proportional to the configured per-key allowance. Benchmark Redis CPU, memory, and latency with realistic key counts and limits before claiming production capacity. A token bucket or approximate sliding counter uses less state but has different burst/boundary semantics.

## Key storage and revocation

Keys are generated with high entropy and returned only at creation. PostgreSQL stores an HMAC digest made with a separate pepper; the pepper must be at least 32 characters and must be kept outside source control. Redis caches key/policy metadata for 10 seconds. Revocation updates PostgreSQL and deletes the metadata and counter keys from Redis.

The database and Redis cannot participate in one atomic transaction. If Redis is unavailable during revocation, the database key is revoked but Redis invalidation may fail; the request returns 503 and the short metadata TTL bounds stale cache lifetime. A production system should use a transactional outbox or another durable invalidation mechanism if that residual window is unacceptable.

## Failure behavior

When rate limiting is enabled, missing Redis, PostgreSQL, or API-key pepper fails closed with 503. There is no per-process fallback because that would multiply a caller's allowance across workers. The local Redis container uses `noeviction`; memory pressure causes requests to fail closed rather than evicting counters and silently resetting limits.