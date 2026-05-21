"""Centralized logging configuration using structlog with JSON output."""

import logging
import os
import sys

import structlog


def setup_logging(level: str | None = None) -> None:
    """Configure structlog with JSON rendering for production use.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               Falls back to LOG_LEVEL env var or INFO.
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()

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
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger bound to the given module name."""
    return structlog.get_logger(name)
