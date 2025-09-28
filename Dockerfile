FROM python:3.11-slim AS base

# Configure deterministic Python runtime behavior and keep pip chatty for CI diagnostics
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install compilation toolchain and postgres headers for psycopg binary wheels fallback
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pin working directory for subsequent COPY statements
WORKDIR /app

# Copy pyproject metadata up-front so Docker cache survives frequent source edits
COPY pyproject.toml ./

# Use pip's PEP 517 installer to resolve dependencies declared inside pyproject.toml
# This keeps a single source of truth while still leveraging the ubiquitous pip cli
RUN pip install --upgrade pip \
    && pip install -e .[dev]

# Bring in application, migrations and helper scripts after dependencies are baked in
COPY ./src ./src
COPY ./alembic ./alembic
COPY ./scripts ./scripts

# Expose src to Python for interactive shells and celery workers
ENV PYTHONPATH=/app/src

# Ensure helper scripts are executable inside slim base images
RUN chmod +x /app/scripts/*.sh

# Delegate process supervision to the Bash entrypoint (runtime mode decided there)
CMD ["/app/scripts/entrypoint.sh"]
