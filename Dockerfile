FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies against a stub package first, so code-only rebuilds reuse this layer.
COPY pyproject.toml ./
RUN mkdir -p src/pidm && touch src/pidm/__init__.py && pip install . && rm -rf src build

COPY src ./src
RUN pip install --no-deps . && rm -rf build

# UID 1000 matches the default first user on Raspberry Pi OS, so host-created bind-mount folders are writable.
RUN useradd --uid 1000 --create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "pidm.app:app", "--host", "0.0.0.0", "--port", "8000"]
