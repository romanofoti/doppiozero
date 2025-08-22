"""
search_github_conversations.py
Module for searching GitHub conversations using a query string and returning metadata for each result.
"""

from typing import List, Dict, Any
import random


def search_github_conversations(search_query: str) -> List[Dict[str, Any]]:
    """
    Search GitHub conversations using a query string and return metadata for each result.

    Args:
        search_query (str): GitHub search query string.

    Returns:
        List[Dict[str, Any]]: List of metadata for each conversation found.
    """
    # Step 1: Simulate search results (replace with real API call in production)
    results = []
    for i in range(1, 6):
        results.append(
            {
                "url": f"https://github.com/octocat/Hello-World/issues/{100+i}",
                "title": f"Issue {100+i} matching '{search_query}'",
                "updated_at": f"2025-08-{10+i:02d}T12:00:00Z",
                "type": "issue",
                "score": round(random.uniform(0.7, 1.0), 2),
            }
        )
    return results
