# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer cache optimisation)
COPY pyproject.toml uv.lock ./

# Export pinned requirements and install into /app/.venv
RUN uv export --frozen --no-dev -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt --target=/app/packages

# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.11-slim AS production

# Create non-root user for security
RUN addgroup --system --gid 1001 django && \
    adduser  --system --uid 1001 --ingroup django --no-create-home django

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/packages /app/packages

# Set PYTHONPATH so packages are importable
ENV PYTHONPATH="/app/packages:$PYTHONPATH"

# Copy project source
COPY --chown=django:django . .

# Runtime environment defaults (override via Railway env vars)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8000

# Collect static files (SECRET_KEY placeholder for build step only)
RUN SECRET_KEY=build-time-placeholder \
    DEBUG=False \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

# Switch to non-root user
USER django

EXPOSE 8000

# Entrypoint: migrate then start Daphne (ASGI, required for Django Channels)
COPY --chown=django:django entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
