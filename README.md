# ScalePulse Gateway

ScalePulse is a FastAPI edge gateway with PostgreSQL-backed tenant, API-key, and rate-limit policy
management; Redis-backed per-key sliding-window enforcement; and request latency headers.

## Features

- Exact sliding-window limits shared across workers through an atomic Redis Lua script.
- High-entropy API keys, stored as HMAC-SHA-256 digests and returned only once.
- Admin endpoints protected by a configurable bearer token.
- `429` responses include `Retry-After` and rate-limit headers; Redis failures fail closed with 503.
- `/health` is liveness-only; `/ready` checks PostgreSQL and Redis configuration/availability.
- Pure ASGI latency measurement in `x-scalepulse-latency-ms`.

Telemetry ingestion, Kafka, and Cassandra query services are not wired into the gateway yet.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/), Docker, and OpenSSL. On first setup, copy
`.env.example` to `.env`. Run `openssl rand -hex 32` twice and put the two generated values in
`.env` as `SCALEPULSE_ADMIN_TOKEN` and `SCALEPULSE_API_KEY_PEPPER`. Keep both values private.

```sh
uv sync
make docker-up
make test
make lint
curl -i http://localhost:8000/ready
```

Run `make test-integration` with Redis running to verify the atomic concurrent limit behavior.

`make docker-up` applies PostgreSQL migrations and starts the gateway, PostgreSQL, and Redis with
persistent volumes. Cassandra is optional; start it with `make cassandra-up` and apply its schema
with `make cassandra-schema`. `make docker-down` stops the services but preserves volumes.

## Provision a Key

Admin endpoints require `Authorization: Bearer $SCALEPULSE_ADMIN_TOKEN`. Create a tenant, a policy,
and a key in order. The API key secret is returned only once; save it securely.

```sh
curl -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $SCALEPULSE_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"example-tenant"}'

curl -X POST http://localhost:8000/api/v1/admin/tenants/<TENANT_ID>/policies \
  -H "Authorization: Bearer $SCALEPULSE_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"standard","request_limit":100,"window_ms":60000}'

curl -X POST http://localhost:8000/api/v1/admin/tenants/<TENANT_ID>/policies/<POLICY_ID>/api-keys \
  -H "Authorization: Bearer $SCALEPULSE_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Send the returned secret as `X-API-Key` to `/api/v1/resource`. Limits are per key, shared through
Redis, and policies use milliseconds. Revoke a key with
`DELETE /api/v1/admin/tenants/<TENANT_ID>/api-keys/<API_KEY_ID>`.

For Locust, put the issued test key in `.env` as `SCALEPULSE_BENCH_API_KEY`; `make bench` loads it
without printing it in the command output.

Study notes and the historical Day 1 benchmark live separately in [docs](docs/README.md). The
sliding-window design, cache behavior, and trade-offs are described in
[docs/rate-limiting.md](docs/rate-limiting.md).
