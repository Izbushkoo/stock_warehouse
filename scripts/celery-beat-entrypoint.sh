#!/bin/bash
set -euo pipefail

export PYTHONPATH="/app/src:${PYTHONPATH:-}"

# Initialize Celery Beat tables
python /app/scripts/init_celery_beat.py

# Skip scheduler sync for now and run beat directly
exec celery -A warehouse_service.tasks.celery_app:celery \
  beat -l info -S sqlalchemy_celery_beat.schedulers:DatabaseScheduler
