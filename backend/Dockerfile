# Multi-stage: the toolchain that installs the dependencies never reaches the
# runtime image.
#
# The single-stage version carried build-essential and g++ because scikit-learn
# and fastText had to be compiled. Neither is a dependency any more, and every
# remaining package ships a manylinux wheel, so nothing needs a compiler at all.
# The builder stage exists only to keep pip's working files out of the final
# layers.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /build

# Installed into a virtualenv so the whole dependency tree is one directory to
# copy, with no site-packages archaeology in the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# PIP_ONLY_BINARY above makes this fail loudly if a dependency ever stops
# shipping a wheel, rather than silently pulling a compiler back in.
RUN pip install --no-cache-dir .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# curl is the only runtime package: the healthcheck below uses it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

COPY app ./app

# Only the operational scripts ship. gold.py and evaluate.py are dev-time
# tooling and stay out of the runtime image; nothing in production ever needs
# to evaluate the lexicon, only to apply it.
COPY scripts/__init__.py scripts/seed.py scripts/seed_data.py ./scripts/

# Run as a non-root user. The image handles complaint text and attachments from
# the public, so a container escape should not start as root.
RUN useradd --system --uid 10001 --no-create-home rakib \
    && chown -R rakib:rakib /app
USER rakib

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
