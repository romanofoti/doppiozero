"""
search_github_conversations.py

Simple GitHub search wrapper that delegates to the PyGithub adapter.
"""

from typing import List, Dict, Any, Optional
import os


def search_github_conversations(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    token = os.environ.get("GITHUB_TOKEN")
    client = GitHubClient(token)
    results = client.search_issues(query, max_results=max_results)
    return results[:max_results]
