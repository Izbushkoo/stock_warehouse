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

3. Install local tooling directly from `pyproject.toml` (creates a project-local `.venv`):

   ```bash
   make install
   ```

   > ℹ️  The `install` target provisions (or reuses) `.venv` and runs `pip install -e .[dev]` inside it. This sidesteps the PEP 668 "externally managed environment" guardrail by avoiding the system interpreter altogether. You can either rely on `make` targets that call `./.venv/bin/...` directly or activate the environment manually via `source .venv/bin/activate` when working locally.

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
- `make celery-sync` – sync configured periodic tasks into the SQLAlchemy-backed Celery beat tables.
- `make check` – run Ruff linting followed by pytest.

### Frontend development

- Основной код React-приложения расположен в каталоге [`frontend/`](frontend/).
- Для локальной разработки достаточно поднять весь стек через `make local-up` — будет запущен сервис `frontend` с Vite dev server на порту `5173`.
- Переменная `VITE_API_BASE_URL` управляет тем, куда отправляются запросы с фронтенда. По умолчанию она указывает на локальный FastAPI (`http://localhost:8000`).
- В production-профиле Docker Compose строит статический бандл и публикует его на порту `4173`. При необходимости можно переопределить `FRONTEND_PORT` или `FRONTEND_API_BASE_URL` в `.env`.

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
- **Celery** worker and beat leveraging the PostgreSQL-backed `sqlalchemy-celery-beat` scheduler for the daily 09:00 (Europe/Minsk) health report.
- **Redis** for background job brokering and cache-like features.
- **Telegram** notifications for startup diagnostics and scheduled health summaries.
- **React + Vite** фронтенд (каталог `frontend/`), который предоставляет клиентский интерфейс для авторизации и регистрации. Фронт запускается через отдельный контейнер `frontend` в docker-compose и использует REST API FastAPI.

The `scripts/entrypoint.sh` script orchestrates migrations, system checks, and process manager selection so both compose profiles share the same runtime skeleton.
