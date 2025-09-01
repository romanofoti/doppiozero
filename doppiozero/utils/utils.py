"""
utils.py
Shared utility functions for agentic workflows.
"""

import os
import json
import logging
import sys
from typing import Optional

# **********************************
# Constants and parameters
# **********************************

FORMAT = (
    "%(asctime)s - %(name)-10s - %(filename)-18s - %(funcName)-12s - "
    "%(levelname)-8s - %(message)s"
)  # noqa

logging.basicConfig(format=FORMAT, level=logging.INFO)


# **********************************
# Functions definition
# **********************************


def get_logger(name=None, level=logging.INFO, format=FORMAT):
    """Return a logger of the specified name and level.

    Args:
        name : the name of the logger. If no name is specified, root logger is returned.
        level : logging level (e.g. logging.INFO, logging.WARNING, etc.).
        format : format for the logger.

    Returns:
        A configured ``logging.Logger`` instance.

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
    """Read JSON from a file and return the parsed object.

    Args:
        path : Path to the JSON file to read.

    Returns:
        The parsed Python object from the JSON file.

    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    """Write a Python object to a JSON file (pretty-printed).

    Args:
        path : Destination file path.
        data : The Python object to serialize as JSON.

    Returns:
        None

    """
    # Ensure parent directory exists
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json_or_none(path):
    """Read JSON from path, return None if file doesn't exist or can't be read.

    Args:
        path : Path to the JSON file.

    Returns:
        The parsed JSON object, or None when the file is missing or unreadable.

    """
    if not os.path.exists(path):
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def write_json_safe(path, data, indent: int = 2):
    """Write JSON to path, creating parent directories and pretty-printing by default.

    Args:
        path : Path to write the JSON file.
        data : The object to serialize as JSON.
        indent : Number of spaces to use for pretty-printing (default: 2).

    Returns:
        None

    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)


def ensure_dir(path):
    """Ensure the given directory path exists, creating it if necessary.

    Args:
        path : Directory path to create.

    Returns:
        None

    """
    os.makedirs(path, exist_ok=True)


def read_urls_from_stdin_or_file(path: Optional[str]):
    """Return a list of URLs from a file path or stdin (if path is None).

    Args:
        path : Optional path to a file containing one URL per line. If None,
               URLs are read from stdin.

    Returns:
        A list of URL strings.

    """
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    else:
        data = sys.stdin.read()
        return [line.strip() for line in data.splitlines() if line.strip()]


def safe_filename_for_url(url: str) -> str:
    """Generate a filesystem-safe filename fragment for a url.

    Args:
        url : The URL to convert into a safe filename fragment.

    Returns:
        A string suitable for use as a filename fragment.

    """
    s = url.replace("https://", "")
    s = s.replace("http://", "")
    s = s.replace("/", "_")
    s = s.replace(":", "_")
    return s


ARRAY_FIELDS = ["labels", "topics", "participants"]


def build_qdrant_filters(filter_args):
    """Build a Qdrant-friendly filter object from CLI filter args.

    filter_args - dict or list of strings in key:value form

    Returns a dict representing a qdrant `filter` body. This is a
    conservative port covering common cases: exact match on scalars,
    membership checks for array fields, and created_after/created_before
    as range checks on `created_at`.
    """
    if not filter_args:
        return None

    # Normalize into dict
    if isinstance(filter_args, list):
        filter_dict = {}
        for f in filter_args:
            if ":" in f:
                k, v = f.split(":", 1)
                filter_dict[k] = v
    elif isinstance(filter_args, dict):
        filter_dict = filter_args
    else:
        return None

    must = []
    for k, v in filter_dict.items():
        if k in ("created_after", "created_before"):
            # Range condition on created_at
            # qdrant expects format like: { key: "created_at", range: {gte/lt: ...}}
            if k == "created_after":
                must.append({"key": "created_at", "range": {"gte": v}})
            else:
                must.append({"key": "created_at", "range": {"lte": v}})
        elif k in ARRAY_FIELDS:
            # membership test for array fields
            must.append({"key": k, "match": {"value": v}})
        else:
            # scalar equality / match
            must.append({"key": k, "match": {"value": v}})

    if not must:
        return None
    return {"must": must}


def load_json_if_exists(path: Optional[str]):
    """Load JSON if the given path exists, otherwise return None.

    Args:
        path : Optional path to a JSON file.

    Returns:
        The parsed JSON object or None when path is None or file is missing.

    """
    if not path:
        return None
    if not os.path.exists(path):
        return None
    return read_json_or_none(path)


def save_json(path: str, obj) -> None:
    """Save an object to a JSON file via the safe writer.

    Args:
        path : Destination file path.
        obj : Python object to serialize.

    Returns:
        None

    """
    write_json_safe(path, obj)
