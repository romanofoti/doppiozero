"""
fetch_github_conversation.py

Helpers for fetching GitHub issues, pull requests, and discussions.

Strategy:
- Prefer the `gh` CLI when present for complex pagination and GraphQL convenience.
- Fallback to GitHub REST API using an access token from the GITHUB_TOKEN
  environment variable.
- Provides caching helpers and updated_at checking to mirror the original
  scripts behavior.
"""

from typing import Optional, Dict, Any, Tuple
import os
import json
import datetime
import urllib.parse

# Use the PyGithub-based adapter
from .github_client import GitHubClient
from .utils.utils import read_json_or_none, write_json_safe


class ContentFetcher:
    """Encapsulates fetching and caching of GitHub conversation content.

    This class wraps the existing helper functions and exposes a single
    `fetch_github_conversation` method. It accepts an optional token to
    create a `GitHubClient` instance when fetching.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def parse_content_info(self, input_str: str) -> Tuple[str, str, str, str]:
        """Accept either a URL or owner/repo/type/number and return components.

        Returns (owner, repo, type, number)
        """
        input_str = input_str.strip()
        # URL form
        if input_str.startswith("http"):
            # Expect URLs like https://github.com/owner/repo/issues/123
            parts = urllib.parse.urlparse(input_str)
            path = parts.path.lstrip("/")
            segs = path.split("/")
            if len(segs) >= 4:
                owner, repo, type_, number = segs[0], segs[1], segs[2], segs[3]
                return owner, repo, type_, number
            raise ValueError(f"Unrecognized GitHub URL: {input_str}")
        # owner/repo/type/number
        segs = input_str.split("/")
        if len(segs) == 4:
            return segs[0], segs[1], segs[2], segs[3]
        raise ValueError(f"Unrecognized input: {input_str}")

    # --- Cache helpers (private) ---
    def _cache_path_for(
        self, cache_root: str, owner: str, repo: str, type_: str, number: str
    ) -> str:
        # conversations/<owner>/<repo>/<type>/<number>.json
        return os.path.join(cache_root, "conversations", owner, repo, type_, f"{number}.json")

    def _load_cache(self, path: str) -> Optional[Dict[str, Any]]:
        return read_json_or_none(path)

    def _save_cache(self, path: str, data: Dict[str, Any]) -> None:
        write_json_safe(path, data)

    def _get_updated_at(self, data: Dict[str, Any], type_: str) -> Optional[str]:
        # Attempt to return an ISO8601 updated_at from the fetched data
        if not data:
            return None
        # After normalization, prefer 'updated_at'
        if isinstance(data, dict):
            return data.get("updated_at") or data.get("updatedAt")
        return None

    def fetch_issue(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        client = GitHubClient(self.token)
        return client.fetch_issue(owner, repo, number)

    def fetch_pr(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        client = GitHubClient(self.token)
        return client.fetch_pr(owner, repo, number)

    def fetch_discussion(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        try:
            client = GitHubClient(self.token)
            return client.fetch_discussion(owner, repo, number)
        except Exception:
            return {
                "url": f"https://github.com/{owner}/{repo}/discussions/{number}",
                "number": number,
            }

    def fetch_github_conversation(
        self,
        conversation_input: str,
        cache_path: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        owner, repo, type_, number = self.parse_content_info(conversation_input)

        # Check cache
        if cache_path:
            cache_file = self._cache_path_for(cache_path, owner, repo, type_, number)
            cached = self._load_cache(cache_file)
            if cached and updated_at:
                try:
                    cached_updated = datetime.datetime.fromisoformat(
                        cached.get("updated_at", "").replace("Z", "+00:00")
                    )
                    updated_at_dt = datetime.datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    if cached_updated and cached_updated >= updated_at_dt:
                        return cached
                except Exception:
                    pass

        # Fetch based on type
        if type_ in ("issue", "issues"):
            data = self.fetch_issue(owner, repo, number)
        elif type_ in ("pull", "pulls", "pr", "prs"):
            data = self.fetch_pr(owner, repo, number)
        elif type_ in ("discussion", "discussions"):
            data = self.fetch_discussion(owner, repo, number)
        else:
            raise ValueError(f"Unknown conversation type: {type_}")
        # Try updated_at filter
        fetched_updated = self._get_updated_at(data if isinstance(data, dict) else {}, type_)
        if updated_at and fetched_updated:
            try:
                fetched_dt = datetime.datetime.fromisoformat(fetched_updated.replace("Z", "+00:00"))
                updated_at_dt = datetime.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if fetched_dt <= updated_at_dt:
                    return {}
            except Exception:
                pass

        # Cache
        if cache_path:
            cache_file = self._cache_path_for(cache_path, owner, repo, type_, number)
            try:
                self._save_cache(cache_file, data)
            except Exception:
                pass

        return data


# Module-level default instance for convenience
content_fetcher = ContentFetcher()
