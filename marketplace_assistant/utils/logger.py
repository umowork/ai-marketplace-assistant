"""Centralized logging configuration."""

import logging
import sys


def setup_logging(level: str | None = None) -> logging.Logger:
    """Настройка логирования для всего приложения.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
               Если None — берётся из LOG_LEVEL env или INFO.

    Returns:
        Корневой логгер.
    """
    import os

    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    # Avoid duplicate handlers
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers[0] = handler

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Получить логгер для конкретного модуля."""
    return logging.getLogger(name)
