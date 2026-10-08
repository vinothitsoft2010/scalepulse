.PHONY: install run run-prod test lint fmt bench docker-up docker-down

WORKERS ?= 4
PORT ?= 8000
USERS ?= 200
SPAWN_RATE ?= 50
DURATION ?= 60s
HOST ?= http://localhost:$(PORT)
NAME ?= baseline
PROCESSES ?= 1

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

run-prod:
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --workers $(WORKERS) --no-access-log

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

bench:
	mkdir -p benchmarks/results
	uv run locust -f tests/load/benchmark_locust.py --headless --processes $(PROCESSES) \
		-u $(USERS) -r $(SPAWN_RATE) -t $(DURATION) --host $(HOST) \
		--csv benchmarks/results/$(NAME)

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
