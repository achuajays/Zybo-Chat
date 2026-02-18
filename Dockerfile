# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer cache optimisation)
COPY pyproject.toml uv.lock ./

# Install all dependencies into a virtual environment
RUN uv sync --frozen --no-dev

# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.11-slim AS production

# Create non-root user
RUN addgroup --system --gid 1001 django && \
    adduser  --system --uid 1001 --ingroup django --no-create-home django

WORKDIR /app

# Copy the virtual environment from builder (includes daphne on PATH)
COPY --from=builder /app/.venv /app/.venv

# Make venv binaries available (daphne, django-admin, etc.)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8000

# Copy project source
COPY --chown=django:django . .

# Create a writable directory for SQLite database, owned by django user
RUN mkdir -p /data && chown django:django /data

# Collect static files
RUN SECRET_KEY=build-time-placeholder \
    DEBUG=False \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

# Copy and prepare entrypoint
COPY --chown=django:django entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
