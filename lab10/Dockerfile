# syntax=docker/dockerfile:1

# ---------- stage 1: build the wheel ----------
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m build --wheel --outdir /dist

# ---------- stage 2: runtime image ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:////data/experiments.db

RUN useradd --create-home --uid 10001 app \
    && mkdir /data && chown app:app /data
WORKDIR /app

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations

USER app
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status != 200)"

# apply migrations, then start the API
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn experiment_registry.api:app --host 0.0.0.0 --port 8000"]
