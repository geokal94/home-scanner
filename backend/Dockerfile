# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

# Install Poetry
ENV POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (cached layer)
COPY pyproject.toml ./
RUN poetry install --only main --no-root

# Copy code
COPY home_scanner/ ./home_scanner/
COPY alembic.ini ./
COPY alembic/ ./alembic/

RUN poetry install --only main

# Fly.io provides PORT env var; default to 8080 for local docker run
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m home_scanner serve --port ${PORT}"]
