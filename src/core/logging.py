"""Structured JSON logging - Loki uyumlu."""

from __future__ import annotations

import logging
import sys

import structlog

from src.config import settings


def setup_logging() -> None:
    """Uygulama genelinde structured logging yapılandır."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Standart logging'i de structlog'a yönlendir
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """İsimlendirilmiş logger döndür."""
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(module=name)
    return logger
