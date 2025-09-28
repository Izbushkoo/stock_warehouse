#!/bin/bash
# Harden the shell for predictable container lifecycle management
set -euo pipefail

# Make sure application sources are importable for alembic and celery at runtime
export PYTHONPATH="/app/src:${PYTHONPATH:-}"

# Apply outstanding migrations before the API boots so schema stays current
alembic upgrade head

# Run synchronous health diagnostics and notify the critical Telegram channel
python -m warehouse_service.system_checks.startup --notify

# Switch process managers based on declared runtime profile
runtime="${APP_RUNTIME:-local}"
case "${runtime}" in
  production)
    workers="${GUNICORN_WORKERS:-6}"
    # Gunicorn with uvicorn workers for multiprocess production execution
    exec gunicorn "warehouse_service.app:create_app" \
      --factory \
      --bind "0.0.0.0:8000" \
      --workers "${workers}" \
      --worker-class "uvicorn.workers.UvicornWorker"
    ;;
  *)
    workers="${UVICORN_WORKERS:-2}"
    # Uvicorn provides a lightweight multiprocess server for local development
    exec uvicorn warehouse_service.app:create_app \
      --factory \
      --host 0.0.0.0 \
      --port 8000 \
      --workers "${workers}"
    ;;
esac
