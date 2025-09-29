-include .env

# Keep project level knobs configurable without editing the Makefile
PROJECT_NAME ?= warehouse
PYTHON ?= python3
COMPOSE_LOCAL_FILE ?= docker-compose.local.yml
COMPOSE_PROD_FILE ?= docker-compose.prod.yml

export PROJECT_NAME

# Helper macros hide the verbose docker compose flags for each stack profile
define compose_local
docker compose -p $(PROJECT_NAME)-local -f $(COMPOSE_LOCAL_FILE)
endef

define compose_prod
docker compose -p $(PROJECT_NAME)-prod -f $(COMPOSE_PROD_FILE)
endef

.PHONY: help install lint test format check \ \
        local-build local-up local-down local-logs local-ps local-migrate local-revision local-shell local-create-admin create-admin setup-user-cleanup list-cleanup-schedules \ \
        prod-build prod-up prod-down prod-logs prod-ps prod-migrate prod-revision prod-shell prod-create-admin \ \
        celery-shell

help:
	@echo "Available commands:"
	@echo "  make install            Install dependencies locally"
	@echo "  make lint               Run static analysis"
	@echo "  make test               Run the unit test suite"
	@echo "  make check              Run lint and tests"
	@echo "  make local-build        Build local development images"
	@echo "  make local-up           Start the local stack with uvicorn"
	@echo "  make local-down         Stop the local stack"
	@echo "  make local-logs         Tail logs from the local stack"
	@echo "  make local-migrate      Apply database migrations in local stack"
	@echo "  make local-revision msg=...  Create Alembic revision via local stack"
	@echo "  make local-shell        Exec into the local app container"
	@echo "  make local-create-admin Create system administrator in local stack"
	@echo "  make create-admin       Create system administrator (local dev, no Docker)"
	@echo "  make setup-user-cleanup Setup periodic user cleanup schedule"
	@echo "  make list-cleanup-schedules List all cleanup schedules"
	@echo "  make prod-build         Build production images"
	@echo "  make prod-up            Start the production stack with gunicorn"
	@echo "  make prod-down          Stop the production stack"
	@echo "  make prod-logs          Tail logs from the production stack"
	@echo "  make prod-migrate       Apply migrations in the production stack"
	@echo "  make prod-revision msg=...  Create Alembic revision via production stack"
	@echo "  make prod-shell         Exec into the production app container"
	@echo "  make prod-create-admin  Create system administrator in production stack"
	@echo "  make celery-shell       Open a Celery shell in the active stack"

install:

	@# Provision a project-local virtual environment for tooling isolation
	@if [ ! -d .venv ]; then \
		$(PYTHON) -m venv .venv; \
	fi
	@# Install editable project dependencies using the local virtual environment
	@./.venv/bin/pip install -e .[dev]

lint:
	# Static code analysis keeps quality high before hitting CI
	ruff check src tests

format:
	# Auto-fixable linting shortcut for quick refactors
	ruff check --fix src tests

test:
	# Run Python unit tests locally
	pytest

check: lint test

local-build:
	# Build local images so compose up starts instantly afterwards
	$(compose_local) build

local-up:
	# Boot the local stack, run startup diagnostics and display container status
	$(compose_local) up -d
	$(compose_local) exec app python -m warehouse_service.system_checks.startup --notify
	$(compose_local) ps

local-down:
	# Stop the local stack and prune volumes for a clean slate
	$(compose_local) down -v

local-logs:
	# Tail logs from all services in the local stack
	$(compose_local) logs -f --tail=200

local-ps:
	# Show container status for the local stack
	$(compose_local) ps

local-migrate:
	# Apply Alembic migrations inside the local application container
	$(compose_local) exec app alembic upgrade head

local-revision:
	# Generate a new migration from model diffs via the local stack
	$(compose_local) exec app alembic revision --autogenerate -m "$(msg)"

local-shell:
	# Open an interactive shell inside the local app container
	$(compose_local) exec app bash

local-create-admin:
	# Create system administrator in local stack
	$(compose_local) exec app python scripts/create_admin_unified.py

create-admin:
	# Create system administrator (local development, no Docker)
	python scripts/create_admin_unified.py

setup-user-cleanup:
	# Setup periodic user cleanup schedule
	python scripts/setup_user_cleanup_schedule.py

list-cleanup-schedules:
	# List all cleanup schedules
	python scripts/setup_user_cleanup_schedule.py list

prod-build:
	# Build production tagged images
	$(compose_prod) build

prod-up:
	# Boot the production stack, trigger health diagnostics and show status
	$(compose_prod) up -d
	$(compose_prod) exec app python -m warehouse_service.system_checks.startup --notify
	$(compose_prod) ps

prod-down:
	# Stop the production stack (volumes kept for data safety)
	$(compose_prod) down

prod-logs:
	# Tail logs from all production services
	$(compose_prod) logs -f --tail=200

prod-ps:
	# Show container status for the production stack
	$(compose_prod) ps

prod-migrate:
	# Apply migrations inside the production app container
	$(compose_prod) exec app alembic upgrade head

prod-revision:
	# Create new Alembic revision via production container (useful for remote envs)
	$(compose_prod) exec app alembic revision --autogenerate -m "$(msg)"

prod-shell:
	# Shell into the production app container for debugging
	$(compose_prod) exec app bash

prod-create-admin:
	# Create system administrator in production stack
	$(compose_prod) exec app python scripts/create_admin_unified.py

celery-shell:
        # Connect to the Celery shell using STACK=local (default) or STACK=prod
        @stack=${STACK:-local}; \
        if [ "$$stack" = "prod" ]; then \
        $(compose_prod) exec worker celery shell -A warehouse_service.tasks.celery_app:celery; \
        else \
        $(compose_local) exec worker celery shell -A warehouse_service.tasks.celery_app:celery; \
        fi

celery-sync:
        # Persist configured periodic tasks to the SQLAlchemy beat backend
        @stack=${STACK:-local}; \
        if [ "$$stack" = "prod" ]; then \
        $(compose_prod) run --rm beat python -m warehouse_service.tasks.scheduler_sync; \
        else \
        $(compose_local) run --rm beat python -m warehouse_service.tasks.scheduler_sync; \
        fi
