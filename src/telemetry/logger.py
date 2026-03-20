"""Structured logging for the AI Abyss system."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("ai_abyss")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("ai_abyss")


def log_classification(
    ip: str,
    path: str,
    classification: str,
    score: float,
    signals: dict[str, Any] | None = None,
) -> None:
    logger = get_logger()
    logger.info(
        "CLASSIFY ip=%s path=%s result=%s score=%.3f signals=%s",
        ip,
        path,
        classification,
        score,
        signals,
    )


def log_killchain(ip: str, path: str, layers: list[str]) -> None:
    logger = get_logger()
    logger.info("KILLCHAIN ip=%s path=%s layers=%s", ip, path, ",".join(layers))


def log_callback(canary_token: str, ip: str, vector: str | None = None) -> None:
    logger = get_logger()
    logger.warning("CALLBACK canary=%s ip=%s vector=%s", canary_token, ip, vector)
