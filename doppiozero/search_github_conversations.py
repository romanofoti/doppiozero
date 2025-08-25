"""
search_github_conversations.py

Simple GitHub search wrapper using the REST Search API as a fallback. Returns
minimal metadata for each matched conversation: url and updated_at.
"""

from typing import List, Dict, Any, Optional
import os
import urllib.parse
from .fetch_github_conversation import _http_get_json, DEFAULT_API_BASE


def _search_issues_rest(
    query: str, token: Optional[str], per_page: int = 50
) -> List[Dict[str, Any]]:
    encoded = urllib.parse.quote(query)
    url = f"{DEFAULT_API_BASE}/search/issues?q={encoded}&per_page={per_page}"
    resp = _http_get_json(url, token=token)
    items = resp.get("items", []) if isinstance(resp, dict) else []
    results = []
    for it in items:
        # items contain html_url and updated_at
        results.append({"url": it.get("html_url"), "updated_at": it.get("updated_at")})
    return results


def search_github_conversations(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    token = os.environ.get("GITHUB_TOKEN")
    # Use REST search for issues/PRs/discussions as a simple fallback
    results = _search_issues_rest(query, token, per_page=max_results)
    # Truncate to max_results
    return results[:max_results]
