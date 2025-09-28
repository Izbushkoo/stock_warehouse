# Unified Warehouse Service Skeleton

The repository provides the baseline scaffolding for the merged warehouse platform. FastAPI, Celery, PostgreSQL, and Redis are wired together with environment-driven configuration, RBAC-ready models, and Telegram-powered health notifications.

## Environment bootstrap

1. Copy environment configuration to `.env` (shared between local and production stacks):

   ```bash
   cp .env.example .env
   ```

2. Adjust the runtime section inside `.env` when necessary:
   - `APP_RUNTIME=local` keeps the development profile (Uvicorn with two workers).
   - `APP_RUNTIME=production` switches the entrypoint to Gunicorn with six workers by default.

3. Install local tooling directly from `pyproject.toml`:

   ```bash
   make install
   ```

   > ℹ️  The project intentionally uses `pip install -e .` even though it has a `pyproject.toml`. Pip is the PEP 517 front-end that reads the pyproject metadata and builds the editable package, so there is still a single dependency source of truth without introducing an extra package manager.

## Local development workflow

```bash
# Build images once (optional if you rely on on-demand builds)
make local-build

# Start the full stack (runs migrations, startup checks, Telegram alert, and shows container status)
make local-up

# Stream logs from all services
make local-logs

# Apply database migrations
make local-migrate

# Tear down the stack and related volumes
make local-down
```

Additional helpers:

- `make local-shell` – open a shell in the app container.
- `make celery-shell` – open a Celery shell (override with `STACK=prod` for the production stack).
- `make check` – run Ruff linting followed by pytest.

## Production-oriented commands

```bash
# Build images with production naming
make prod-build

# Launch the production stack (Gunicorn + startup checks + Telegram alert)
make prod-up

# Review service status and logs
make prod-ps
make prod-logs

# Apply migrations safely
make prod-migrate

# Shut down containers while keeping persisted volumes
make prod-down
```

## Stack overview

- **FastAPI** application served by Uvicorn (local) or Gunicorn (production) depending on `APP_RUNTIME`.
- **SQLModel** with PostgreSQL for RBAC entities, inventory, and auditing layers.
- **Celery** worker and beat leveraging the PostgreSQL-backed `celery_sqlalchemy_scheduler` for the daily 09:00 (Europe/Minsk) health report.
- **Redis** for background job brokering and cache-like features.
- **Telegram** notifications for startup diagnostics and scheduled health summaries.

The `scripts/entrypoint.sh` script orchestrates migrations, system checks, and process manager selection so both compose profiles share the same runtime skeleton.
