"""
Shared helpers used by the CLI wrapper scripts.

This module centralizes small utilities used by the command-line wrappers so
the heavy lifting remains in the package modules (fetching, summarizing,
indexing, etc.).
"""

from typing import List, Optional
import os
import sys
from .utils import read_json_or_none, write_json_safe


def read_urls_from_stdin_or_file(path: Optional[str]) -> List[str]:
    """Return a list of URLs from a file path or stdin (if path is None).

    If path is None, read from stdin (useful for piping). If path is provided,
    read one URL per line and strip whitespace.

    Args:
        path : Optional path to a file containing URLs, one per line. If None,
               URLs are read from stdin.

    Returns:
        A list of URL strings read from the provided source.

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
        url : The URL to sanitize into a filename fragment.

    Returns:
        A filesystem-safe string derived from the URL.

    """
    s = url.replace("https://", "")
    s = s.replace("http://", "")
    s = s.replace("/", "_")
    s = s.replace(":", "_")
    return s


def load_json_if_exists(path: Optional[str]):
    """Load JSON from a file if the path exists, otherwise return None.

    Args:
        path : Optional filesystem path to a JSON file.

    Returns:
        The parsed JSON object, or None if the file does not exist or path is None.

    """
    if not path:
        return None
    if not os.path.exists(path):
        return None
    return read_json_or_none(path)


def save_json(path: str, obj) -> None:
    """Write an object to a JSON file safely.

    Args:
        path : The destination file path for JSON output.
        obj : The Python object to serialize as JSON.

    Returns:
        None

    """
    write_json_safe(path, obj)
