#!/bin/bash
set -euo pipefail

export PYTHONPATH="/app/src:${PYTHONPATH:-}"

python -m warehouse_service.tasks.scheduler_sync

exec celery -A warehouse_service.tasks.celery_app:celery \
  beat -l info -S sqlalchemy_celery_beat.schedulers:DatabaseScheduler
