.PHONY: install run run-prod test test-integration lint fmt bench docker-up docker-down postgres-up cassandra-up redis-up rate-limit-up data-up db-migrate cassandra-schema data-init data-down data-status db-shell cassandra-shell

WORKERS ?= 4
PORT ?= 8000
USERS ?= 200
SPAWN_RATE ?= 50
DURATION ?= 60s
HOST ?= http://localhost:$(PORT)
NAME ?= baseline
PROCESSES ?= 4
DATABASE_URL ?= postgresql+psycopg://scalepulse:local-only-change-this@localhost:5432/scalepulse

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

run-prod:
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --workers $(WORKERS) --no-access-log

test:
	uv run pytest

test-integration:
	@set -a; if [ -f .env ]; then . ./.env; fi; set +a; uv run pytest tests/integration

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

bench:
	mkdir -p benchmarks/results
	@set -a; if [ -f .env ]; then . ./.env; fi; set +a; \
	uv run locust -f tests/load/benchmark_locust.py --headless --processes $(PROCESSES) \
		-u $(USERS) -r $(SPAWN_RATE) -t $(DURATION) --host $(HOST) \
		--csv benchmarks/results/$(NAME)

docker-up:
	$(MAKE) rate-limit-up

docker-down:
	docker compose --profile data --profile rate-limit down

redis-up:
	docker compose up -d --wait redis

rate-limit-up: db-migrate
	docker compose --profile data up --build -d --wait gateway postgres redis

postgres-up:
	docker compose --profile data up -d --wait postgres

cassandra-up:
	docker compose --profile data up -d --wait cassandra

data-up:
	docker compose --profile data up -d --wait postgres cassandra

db-migrate: postgres-up
	set -a; if [ -f .env ]; then . ./.env; fi; set +a; \
	SCALEPULSE_DATABASE_URL="$${SCALEPULSE_DATABASE_URL:-$(DATABASE_URL)}" uv run alembic upgrade head

cassandra-schema: cassandra-up
	docker compose --profile data run --rm cassandra-schema

data-init:
	$(MAKE) db-migrate
	$(MAKE) cassandra-schema

data-down:
	docker compose --profile data --profile rate-limit stop postgres cassandra redis

data-status:
	docker compose --profile data --profile rate-limit ps

db-shell:
	set -a; if [ -f .env ]; then . ./.env; fi; set +a; \
	docker compose --profile data exec postgres psql -U "$${POSTGRES_USER:-scalepulse}" -d "$${POSTGRES_DB:-scalepulse}"

cassandra-shell:
	docker compose --profile data exec cassandra cqlsh
