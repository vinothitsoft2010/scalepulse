# Day 1: Gateway Baseline

## Goal

Create a runnable FastAPI gateway and measure its cost before adding infrastructure dependencies.

## What was built

- Python 3.12 project managed by uv with a lockfile, Ruff, pytest, Docker, and Compose.
- FastAPI app factory with `GET /health` and `GET /api/v1/resource`.
- Pure ASGI latency interceptor that adds `x-scalepulse-latency-ms` when response headers are sent.
- Locust load profile and smoke tests.

ASGI is the server/application contract: Uvicorn invokes the app with a request scope, receive callable, and send callable. The middleware wraps `send` and edits the `http.response.start` message. It measures app time until response headers, not body streaming or network time.

## Baseline

Apple M3 Pro, 11 cores, 18 GB RAM; 200 Locust users, spawn rate 50, 60 seconds, 4 Locust processes:

| Target | Workers | RPS | p50 | p95 | p99 | Errors |
|---|---:|---:|---:|---:|---:|---:|
| Native | 1 | 17,557 | 7 ms | 13 ms | 19 ms | 0% |
| Native | 4 | 39,661 | 1 ms | 3 ms | 4 ms | 0% |
| Docker Desktop | 4 | 22,482 | 4 ms | 18 ms | 32 ms | 0% |

One Locust process capped around 16k RPS and hid the server's scaling difference. Four processes exposed more of the gateway's capacity. These are local comparative measurements, not production capacity claims. Docker Desktop adds VM and port-forwarding overhead.

## Study prompts

1. Why does `async` help I/O concurrency but not make CPU-bound Python code run across cores?
2. Why is the ASGI response-start message the last point where middleware can add headers?
3. What changes between one and four Uvicorn worker processes?
