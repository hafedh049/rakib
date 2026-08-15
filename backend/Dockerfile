FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir . \
    && apt-get purge -y build-essential g++ \
    && apt-get autoremove -y

COPY app ./app

# Only the operational scripts ship. gold.py and evaluate.py are dev-time
# tooling and stay out of the runtime image; nothing in production ever needs
# to evaluate the lexicon, only to apply it.
COPY scripts/__init__.py scripts/seed.py scripts/seed_data.py ./scripts/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
