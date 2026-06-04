SHELL := /bin/bash
.DEFAULT_GOAL := help

UV ?= uv
IMAGE ?= fpl-agent
API_PORT ?= 8000
FRONTEND_PORT ?= 3000
GAMEWEEK ?= 32
OUTPUT_DIR ?= data/reports/gw$(GAMEWEEK)-local
PER_EXPERT_LIMIT ?= 2
EXPERT_NAME ?=
EXPERT_COUNT ?=
SYNTHESIS ?= 0

.PHONY: help install install-frontend test lint run-api run-frontend run-cli docker-build docker-run docker-down

help:
	@printf "Available targets:\n"
	@printf "  make install       Install project and dev dependencies with uv\n"
	@printf "  make test          Run the pytest suite\n"
	@printf "  make lint          Run Ruff against the repo\n"
	@printf "  make run-api       Start the FastAPI backend\n"
	@printf "  make run-frontend  Start the Next.js frontend\n"
	@printf "  make run-cli       Run the weekly pipeline CLI\n"
	@printf "  make docker-build  Build the backend Docker image\n"
	@printf "  make docker-run    Start the Docker Compose API service\n"
	@printf "  make docker-down   Stop the Docker Compose service\n"

install:
	$(UV) sync --frozen --group dev

install-frontend:
	npm --prefix frontend install

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .

run-api:
	$(UV) run uvicorn src.app.main:app --host 0.0.0.0 --port $(API_PORT)

run-frontend:
	npm --prefix frontend run dev -- --port $(FRONTEND_PORT)

run-cli:
	@args=( \
		--gameweek "$(GAMEWEEK)" \
		--output-dir "$(OUTPUT_DIR)" \
		--per-expert-limit "$(PER_EXPERT_LIMIT)" \
	); \
	if [[ -n "$(EXPERT_NAME)" ]]; then args+=(--expert-name "$(EXPERT_NAME)"); fi; \
	if [[ -n "$(EXPERT_COUNT)" ]]; then args+=(--expert-count "$(EXPERT_COUNT)"); fi; \
	if [[ "$(SYNTHESIS)" != "1" && "$(SYNTHESIS)" != "true" && "$(SYNTHESIS)" != "TRUE" && "$(SYNTHESIS)" != "yes" && "$(SYNTHESIS)" != "YES" ]]; then args+=(--no-synthesis); fi; \
	$(UV) run python -m src.app.cli.run_gameweek_report "$${args[@]}"

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker compose up --build api

docker-down:
	docker compose down
