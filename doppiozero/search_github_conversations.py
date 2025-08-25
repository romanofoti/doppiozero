"""
search_github_conversations.py

Simple GitHub search wrapper that delegates to the PyGithub adapter.
"""

from typing import List, Dict, Any, Optional
import os
from .github_client import search_issues


def search_github_conversations(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    token = os.environ.get("GITHUB_TOKEN")
    results = search_issues(query, max_results=max_results, token=token)
    return results[:max_results]
