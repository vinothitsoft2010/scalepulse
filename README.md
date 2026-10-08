# ScalePulse

Edge gateway middleware platform: Redis sliding-window rate limiting, Kafka telemetry ingestion,
circuit breaking with DLQs, polyglot persistence (PostgreSQL + Cassandra), and an ops dashboard.

## Day 1 scope

- FastAPI gateway core with a pure ASGI latency interceptor (`x-scalepulse-latency-ms` header)
- Smoke tests (pytest) and load tests (Locust)
- Docker image + Compose (gateway only)
- Baseline throughput/latency before Redis/Kafka are introduced

## Layout

```
app/
  main.py               # create_app() factory, middleware + routers
  core/config.py        # Settings (SCALEPULSE_* env vars)
  middleware/latency.py # LatencyHeaderMiddleware (pure ASGI)
  api/health.py         # GET /health (unversioned, for LB/K8s probes)
  api/v1/router.py      # GET /api/v1/resource (simulated downstream)
tests/
  unit/                 # pytest smoke tests
  load/                 # Locust scenarios
```

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Docker.

```sh
cp .env.example .env
make install      # uv sync (installs Python 3.12 if needed)
make run          # dev server with reload on :8000
make test
make lint
make docker-up    # containerized gateway on :8000
```

Benchmark (in a second terminal, against the non-reload server). Use port 8001 natively if the
Docker gateway already holds 8000:

```sh
make run-prod WORKERS=4 PORT=8001
make bench PORT=8001 NAME=native-w4 PROCESSES=4
```

CSV results are written to `benchmarks/results/<NAME>_*.csv`. Use `PROCESSES=4` or more; a
single Locust process tops out around 16k RPS and becomes the bottleneck.

## Baseline (Day 1)

Machine: Apple M3 Pro, 11 cores, 18 GB RAM (Docker VM: 11 CPUs, ~7.7 GB) — Date: 2026-10-08

Locust: 200 users, spawn rate 50, 60s, 4 processes, 90% `/api/v1/resource` + 10% `/health`.

| Target         | Workers | RPS    | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
|----------------|---------|--------|----------|----------|----------|--------|
| Native uvicorn | 1       | 17,557 | 7        | 13       | 19       | 0%     |
| Native uvicorn | 4       | 39,661 | 1        | 3        | 4        | 0%     |
| Docker         | 4       | 22,482 | 4        | 18       | 32       | 0%     |

Notes: Locust shares the CPU with the server on a laptop, so treat numbers as relative.
Docker Desktop on macOS adds VM and port-forwarding overhead (~43% less RPS than native).
