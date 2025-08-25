"""Simple logging helpers for the doppiozero package.

Provides info, warn, error helpers and a small setup_logger wrapper to
match expectations from the migrated code.
"""

import logging
from typing import Optional


def setup_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s %(levelname)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def _get_default_logger() -> logging.Logger:
    return setup_logger("doppiozero")


def info(msg: str, *args, **kwargs) -> None:
    _get_default_logger().info(msg, *args, **kwargs)


def warn(msg: str, *args, **kwargs) -> None:
    _get_default_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    _get_default_logger().error(msg, *args, **kwargs)


__all__ = ["setup_logger", "info", "warn", "error"]
