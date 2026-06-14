"""Common utilities — mirrors the trivelta helper interface for learning."""

from __future__ import annotations

import logging


def get_logger(name: str, *, service_name: str | None = None) -> logging.Logger:
    """Return a named logger.

    Matching the trivelta helper.utilities.get_logger signature so service
    code is portable between this learning repo and the real repo.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        if service_name:
            logger = logging.LoggerAdapter(logger, {"service": service_name})  # type: ignore[assignment]
    return logger
