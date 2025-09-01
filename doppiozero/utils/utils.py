"""
utils.py
Shared utility functions for agentic workflows.
"""

import os
import json
import logging
import sys
from typing import Optional
import re
import uuid

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


def _split_multi_values(val: str):
    """Split a filter value on commas or pipes into parts, trimming whitespace."""
    return [p.strip() for p in re.split(r"[,|]+", val) if p.strip()]


def _parse_comparison(val: str):
    """Parse a comparison operator at the start of a value, returning (op, rhs) or None."""
    m = re.match(r"^(>=|<=|>|<)\s*(.+)$", val)
    if not m:
        return None
    op, rhs = m.groups()
    return op, rhs.strip()


def build_qdrant_filters(filter_args):
    """Build a Qdrant-friendly filter object from CLI filter args.

    Supports input as a dict (key->value) or a list of 'key:value' strings.

    Features:
    - multi-value filters: 'topics:security,performance' -> should (OR)
    - comparison operators: 'stars:>100', 'created_after:2025-01-01'
    - array-field membership for fields in ARRAY_FIELDS

    Returns a dict suitable for passing as the `filter` body to Qdrant's
    search endpoint, or None when no filters are provided.
    """
    if not filter_args:
        return None

    # Normalize into a dict
    if isinstance(filter_args, list):
        filter_dc = {}
        for f in filter_args:
            if ":" in f:
                k, v = f.split(":", 1)
                filter_dc[k] = v
    elif isinstance(filter_args, dict):
        filter_dc = filter_args
    else:
        return None

    must_ls = []
    should_ls = []

    for k, raw_v in filter_dc.items():
        if raw_v is None:
            continue
        v = str(raw_v).strip()

        # Special date range shorthand
        if k == "created_after":
            must_ls.append({"key": "created_at", "range": {"gte": v}})
            continue
        if k == "created_before":
            must_ls.append({"key": "created_at", "range": {"lte": v}})
            continue

        # Comparison operators (numeric or lexical)
        comp = _parse_comparison(v)
        if comp:
            op, rhs = comp
            rng_dc = {}
            if op == ">":
                rng_dc["gt"] = rhs
            elif op == ">=":
                rng_dc["gte"] = rhs
            elif op == "<":
                rng_dc["lt"] = rhs
            elif op == "<=":
                rng_dc["lte"] = rhs
            must_ls.append({"key": k, "range": rng_dc})
            continue

        # Multi-value (OR) support
        parts_ls = _split_multi_values(v)
        if len(parts_ls) > 1:
            # For array fields, each part is a membership check; otherwise match value
            for p in parts_ls:
                if k in ARRAY_FIELDS:
                    should_ls.append({"key": k, "match": {"value": p}})
                else:
                    should_ls.append({"key": k, "match": {"value": p}})
            continue

        # Single value: for array fields this is a membership/match, else scalar match
        if k in ARRAY_FIELDS:
            must_ls.append({"key": k, "match": {"value": v}})
        else:
            must_ls.append({"key": k, "match": {"value": v}})

    filter_dc = {}
    if must_ls:
        filter_dc["must"] = must_ls
    if should_ls:
        filter_dc["should"] = should_ls

    if not filter_dc:
        return None

    # Prefer to return qdrant-client typed model objects when available
    try:
        # Import model classes from the installed qdrant-client
        from qdrant_client.models import Filter as QFilter
        from qdrant_client.models import FieldCondition as QFieldCondition
        from qdrant_client.models import MatchValue as QMatchValue
        from qdrant_client.models import Range as QRange
    except Exception:
        # qdrant-client not available or different API: return plain dict
        return filter_dc

    def _to_field_condition(cond: dict):
        """Convert a simple condition dict into a Qdrant FieldCondition model."""
        key = cond.get("key")
        if "match" in cond:
            mv = cond["match"].get("value")
            return QFieldCondition(key=key, match=QMatchValue(value=mv))
        if "range" in cond:
            rng = cond["range"]
            # Pass through known keys
            return QFieldCondition(
                key=key,
                range=QRange(
                    gte=rng.get("gte"),
                    lte=rng.get("lte"),
                    gt=rng.get("gt"),
                    lt=rng.get("lt"),
                ),
            )
        # Unknown condition shape: return a FieldCondition with raw payload if possible
        return QFieldCondition(key=key)

    q_must_ls = [_to_field_condition(c) for c in filter_dc.get("must", [])]
    q_should_ls = [_to_field_condition(c) for c in filter_dc.get("should", [])]

    # Build the Qdrant Filter model
    qfilter_kwargs = {}
    if q_must_ls:
        qfilter_kwargs["must"] = q_must_ls
    if q_should_ls:
        qfilter_kwargs["should"] = q_should_ls

    try:
        return QFilter(**qfilter_kwargs)
    except Exception:
        # If constructing the typed model fails, fall back to dict
        return filter_dc


def deterministic_uuid5(name: str, namespace: Optional[str] = None) -> str:
    """Return a deterministic UUID5 string for the given name.

    If `namespace` is provided it is first converted into a UUID using
    the URL namespace; otherwise the standard `uuid.NAMESPACE_URL` is used.

    This helper is useful for producing stable UUIDs from external ids
    (URLs, slugs, etc.) so that repeated upserts use the same point id.
    """
    try:
        if namespace:
            # derive a namespace UUID from the provided namespace string
            namespace_uuid = uuid.uuid5(uuid.NAMESPACE_URL, str(namespace))
        else:
            namespace_uuid = uuid.NAMESPACE_URL
        return str(uuid.uuid5(namespace_uuid, str(name)))
    except Exception:
        # Fallback: return a random uuid4 string if uuid5 construction fails
        return str(uuid.uuid4())


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
