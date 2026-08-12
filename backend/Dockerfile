FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# build deps for fasttext (compiled once, dropped from the runtime layer)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir . \
    && apt-get purge -y build-essential g++ \
    && apt-get autoremove -y

COPY app ./app
COPY ml_artifacts ./ml_artifacts
COPY data ./data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
