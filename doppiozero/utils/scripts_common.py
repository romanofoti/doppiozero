"""
Shared helpers used by the CLI wrapper scripts.

This module centralizes small utilities used by the command-line wrappers so
the heavy lifting remains in the package modules (fetching, summarizing,
indexing, etc.).
"""

from typing import List, Optional
import os
import json
import sys


def read_urls_from_stdin_or_file(path: Optional[str]) -> List[str]:
    """Return a list of URLs from a file path or stdin (if path is None).

    If path is None, read from stdin (useful for piping). If path is provided,
    read one URL per line and strip whitespace.
    """
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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
