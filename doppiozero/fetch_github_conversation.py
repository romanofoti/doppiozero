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

# Use the PyGithub-based adapter
from .github_client import GitHubClient


def parse_input(input_str: str) -> Tuple[str, str, str, str]:
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


def load_cache(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _cache_path_for(cache_root: str, owner: str, repo: str, type_: str, number: str) -> str:
    # conversations/<owner>/<repo>/<type>/<number>.json
    return os.path.join(cache_root, "conversations", owner, repo, type_, f"{number}.json")


def get_updated_at(data: Dict[str, Any], type_: str) -> Optional[str]:
    # Attempt to return an ISO8601 updated_at from the fetched data
    if not data:
        return None
    # After normalization, prefer 'updated_at'
    if isinstance(data, dict):
        return data.get("updated_at") or data.get("updatedAt")
    return None


def fetch_issue(owner: str, repo: str, number: str, token: Optional[str]) -> Dict[str, Any]:
    client = GitHubClient(token)
    return client.fetch_issue(owner, repo, number)


def fetch_pr(owner: str, repo: str, number: str, token: Optional[str]) -> Dict[str, Any]:
    client = GitHubClient(token)
    return client.fetch_pr(owner, repo, number)


def fetch_discussion(owner: str, repo: str, number: str, token: Optional[str]) -> Dict[str, Any]:
    try:
        client = GitHubClient(token)
        return client.fetch_discussion(owner, repo, number)
    except Exception:
        return {"url": f"https://github.com/{owner}/{repo}/discussions/{number}", "number": number}


def fetch_github_conversation(
    conversation_input: str,
    cache_path: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch a conversation (issue, pull request, discussion) and optionally cache it.

    conversation_input may be a GitHub URL or owner/repo/type/number.
    """
    owner, repo, type_, number = parse_input(conversation_input)
    token = os.environ.get("GITHUB_TOKEN")

    # Check cache
    if cache_path:
        cache_file = _cache_path_for(cache_path, owner, repo, type_, number)
        cached = load_cache(cache_file)
        if cached and updated_at:
            try:
                cached_updated = datetime.datetime.fromisoformat(
                    cached.get("updated_at", "").replace("Z", "+00:00")
                )
                updated_at_dt = datetime.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if cached_updated and cached_updated >= updated_at_dt:
                    return cached
            except Exception:
                pass

    # Fetch based on type
    if type_ in ("issue", "issues"):
        data = fetch_issue(owner, repo, number, token)
    elif type_ in ("pull", "pulls", "pr", "prs"):
        data = fetch_pr(owner, repo, number, token)
    elif type_ in ("discussion", "discussions"):
        data = fetch_discussion(owner, repo, number, token)
    else:
        raise ValueError(f"Unknown conversation type: {type_}")

    # Try updated_at filter
    fetched_updated = get_updated_at(data if isinstance(data, dict) else {}, type_)
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
        cache_file = _cache_path_for(cache_path, owner, repo, type_, number)
        try:
            save_cache(cache_file, data)
        except Exception:
            pass

    return data
