"""
fetch_github_conversations.py
Module for fetching and exporting data for multiple GitHub conversations.
"""

from typing import List, Optional, Dict, Any
import os
from .fetch_github_conversation import fetch_github_conversation


def fetch_github_conversations(
    urls: List[str],
    cache_path: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch and export data for multiple GitHub conversations.

    Args:
        urls (List[str]): List of GitHub conversation URLs.
        cache_path (Optional[str]): Directory for caching data (default: None).
        updated_at (Optional[str]): Only fetch if remote conversation is newer than this timestamp.

    Returns:
        List[Dict[str, Any]]: List of conversation data as JSON objects.
    """
    results = []
    for url in urls:
        try:
            convo = fetch_github_conversation(url, cache_path=cache_path, updated_at=updated_at)
            if convo:
                results.append(convo)
        except Exception as e:
            print(f"Error fetching conversation for {url}: {e}")
    return results
