# Builds the web UI; only its built files reach the final image, so Node never ships.
FROM node:22-slim AS web
WORKDIR /web
COPY src/web/package.json src/web/package-lock.json ./
RUN npm ci
COPY src/web ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIDM_DB=/data/pidm.sqlite \
    PIDM_WEB_DIR=/app/web

WORKDIR /app

# Install dependencies against a stub package first, so code-only rebuilds reuse this layer.
COPY pyproject.toml ./
RUN mkdir -p src/pidm && touch src/pidm/__init__.py && pip install . && rm -rf src build

# Bake the embedding model in (ADR 0005); the app user only reads it.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')" && chmod -R a+rX /opt/fastembed

COPY src/pidm ./src/pidm
RUN pip install --no-deps . && rm -rf build
COPY --from=web /web/dist ./web

# UID 1000 matches the default first user on Raspberry Pi OS, so host-created bind-mount folders are writable.
RUN useradd --uid 1000 --create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "pidm.app:from_env", "--factory", "--host", "0.0.0.0", "--port", "8000"]
