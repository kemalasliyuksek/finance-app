"""Alembic migration ortamı - async PostgreSQL desteği."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.models.base import metadata

# Alembic Config nesnesi
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata - tüm model'lerin tabloları burada
target_metadata = metadata


def run_migrations_offline() -> None:
    """Offline migration - SQL üretir."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="trading",
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    # Schema'yı migration'dan önce oluştur (Alembic version tablosu için gerekli)
    connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS trading"))
    connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="trading",
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async migration çalıştır."""
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online migration - veritabanına doğrudan uygular."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
