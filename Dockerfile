FROM python:3.12-slim AS base

# No system packages required: healthcheck uses Python's stdlib urllib instead
# of curl, which keeps the image small and avoids network hits during build.

WORKDIR /app

# Python bağımlılıkları
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Uygulama kodu
COPY . .
RUN pip install --no-cache-dir -e .

# Port
EXPOSE 8000

# Entrypoint: migrasyon + uygulama başlatma
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

CMD ["/app/scripts/entrypoint.sh"]
