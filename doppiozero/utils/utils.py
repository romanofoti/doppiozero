"""
utils.py
Shared utility functions for agentic workflows.
"""

import os
import json
import logging
from typing import Optional

# **********************************
# Constants and parameters
# **********************************

FORMAT = "%(asctime)s - %(name)-10s - %(filename)-18s - %(funcName)-12s - %(levelname)-8s - %(message)s"  # noqa

logging.basicConfig(format=FORMAT, level=logging.INFO)


# **********************************
# Functions definition
# **********************************


def get_logger(name=None, level=logging.INFO, format=FORMAT):
    """Return a logger of the specified name and level.

    Args:
        name   : the name of the logger. If no name is specified, root logger is returned.
        level  : logging levels (e.g. logging.INFO, logging.WARNING, etc.)
        format : format for the logger.

    Multiple calls to getLogger() with the same name return a reference to the same logger object.

    """

    # If no name is specified, return the root logger
    if not name:
        return logging.getLogger()

    # If a logger with the specified name already exists, return it
    logger = logging.getLogger(name)
    if len(logger.handlers) != 0:
        return logger

    # If a logger with the specified name does not exist, create it
    logger.setLevel(level)
    formatter = logging.Formatter(format)

    # Add a StreamHandler to the logger to enable logging to stdout
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # set propagate to False to prevent the logger from propagating to the root logger
    logger.propagate = False
    return logger


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    # Ensure parent directory exists
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json_or_none(path):
    """Read JSON from path, return None if file doesn't exist or can't be read."""
    if not os.path.exists(path):
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def write_json_safe(path, data, indent: int = 2):
    """Write JSON to path, creating parent directories and pretty-printing by default."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


# -------------------------------
# Script/CLI helpers (migrated from scripts_common)
# -------------------------------
def read_urls_from_stdin_or_file(path: Optional[str]):
    """Return a list of URLs from a file path or stdin (if path is None)."""
    import sys

    if path:
        with open(path, "r", encoding="utf-8") as f:
            return [l.strip() for l in f.readlines() if l.strip()]
    else:
        data = sys.stdin.read()
        return [l.strip() for l in data.splitlines() if l.strip()]


def safe_filename_for_url(url: str) -> str:
    """Generate a filesystem-safe filename fragment for a url."""
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_")


def load_json_if_exists(path: Optional[str]):
    if not path:
        return None
    if not os.path.exists(path):
        return None
    return read_json_or_none(path)


def save_json(path: str, obj) -> None:
    write_json_safe(path, obj)
