"""
log.py
Structured logging for agentic workflows.
"""

import logging
from .utils import setup_logger

logger = setup_logger("agent")


def info(msg):
    logger.info(msg)


def warn(msg):
    logger.warning(msg)


def error(msg):
    logger.error(msg)
