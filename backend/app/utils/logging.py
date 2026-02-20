"""Logging configuration for the application."""
from __future__ import annotations

import logging
import sys
from typing import Literal


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger with a clean console handler.

    Call once at application startup.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence overly verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
