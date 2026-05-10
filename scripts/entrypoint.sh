#!/bin/sh
set -e

echo "Veritabanı migrasyonu çalıştırılıyor..."
python -m alembic upgrade head

echo "Uygulama başlatılıyor..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
