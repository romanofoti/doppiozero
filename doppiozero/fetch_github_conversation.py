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
import subprocess
import shlex
import urllib.request
import urllib.parse
import ssl

DEFAULT_API_BASE = "https://api.github.com"


def run_cmd(cmd: str) -> str:
    """Run a shell command and return stdout, raise on error.

    Uses subprocess and returns decoded stdout string.
    """
    proc = subprocess.run(cmd, shell=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {proc.stderr.decode('utf-8')}")
    return proc.stdout.decode("utf-8")


def _http_get_json(url: str, token: Optional[str] = None, accept: Optional[str] = None) -> Any:
    headers = {"User-Agent": "doppiozero-fetcher/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as resp:
        raw = resp.read()
        # If the response is JSON parse it
        return json.loads(raw.decode("utf-8"))


def _http_get_text(url: str, token: Optional[str] = None, accept: Optional[str] = None) -> str:
    headers = {"User-Agent": "doppiozero-fetcher/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as resp:
        return resp.read().decode("utf-8")


def _get_paginated_json(
    url_base: str, token: Optional[str] = None, accept: Optional[str] = None
) -> Any:
    """Fetch paginated JSON results from GitHub REST endpoints.

    Iterates pages using per_page and page query parameters. Returns a list of
    items or a single dict if the endpoint returns an object.
    """
    per_page = 100
    page = 1
    all_items = []
    while True:
        delim = "&" if "?" in url_base else "?"
        url = f"{url_base}{delim}per_page={per_page}&page={page}"
        try:
            data = _http_get_json(url, token=token, accept=accept)
        except Exception:
            break
        if isinstance(data, list):
            all_items.extend(data)
            if len(data) < per_page:
                break
            page += 1
            continue
        return data
    return all_items


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
    # REST endpoint for issue (issue + paginated comments)
    issue = _http_get_json(f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/issues/{number}", token=token)
    comments = _get_paginated_json(
        f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/issues/{number}/comments", token=token
    )
    normalized = {
        "type": "issue",
        "url": issue.get("html_url"),
        "owner": owner,
        "repo": repo,
        "number": int(number),
        "title": issue.get("title"),
        "body": issue.get("body"),
        "user": issue.get("user", {}).get("login"),
        "state": issue.get("state"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "comments": [
            {
                "author": c.get("user", {}).get("login"),
                "body": c.get("body"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
                "url": c.get("html_url") or c.get("url"),
            }
            for c in (comments or [])
        ],
    }
    return normalized


def fetch_pr(owner: str, repo: str, number: str, token: Optional[str]) -> Dict[str, Any]:
    pr = _http_get_json(f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/pulls/{number}", token=token)
    comments = _get_paginated_json(
        f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/issues/{number}/comments", token=token
    )
    reviews = _get_paginated_json(
        f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/pulls/{number}/reviews", token=token
    )
    review_comments = _get_paginated_json(
        f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/pulls/{number}/comments", token=token
    )
    commits = _get_paginated_json(
        f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/pulls/{number}/commits", token=token
    )
    diff = None
    try:
        diff = _http_get_text(
            f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/pulls/{number}",
            token=token,
            accept="application/vnd.github.v3.diff",
        )
    except Exception:
        diff = None

    normalized = {
        "type": "pull_request",
        "url": pr.get("html_url"),
        "owner": owner,
        "repo": repo,
        "number": int(number),
        "title": pr.get("title"),
        "body": pr.get("body"),
        "user": pr.get("user", {}).get("login"),
        "state": pr.get("state"),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
        "comments": [
            {
                "author": c.get("user", {}).get("login"),
                "body": c.get("body"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
                "url": c.get("html_url") or c.get("url"),
            }
            for c in (comments or [])
        ],
        "reviews": [
            {
                "author": r.get("user", {}).get("login"),
                "body": r.get("body"),
                "state": r.get("state"),
                "submitted_at": r.get("submitted_at"),
            }
            for r in (reviews or [])
        ],
        "review_comments": [
            {
                "author": rc.get("user", {}).get("login"),
                "body": rc.get("body"),
                "path": rc.get("path"),
                "position": rc.get("position"),
                "created_at": rc.get("created_at"),
                "updated_at": rc.get("updated_at"),
                "url": rc.get("html_url") or rc.get("url"),
            }
            for rc in (review_comments or [])
        ],
        "commits": [
            {
                "sha": c.get("sha"),
                "message": c.get("commit", {}).get("message"),
                "url": c.get("html_url") or c.get("url"),
            }
            for c in (commits or [])
        ],
        "diff": diff,
    }
    return normalized


def fetch_discussion(owner: str, repo: str, number: str, token: Optional[str]) -> Dict[str, Any]:
    # Discussions are available via REST preview; attempt to fetch via REST
    try:
        return _http_get_json(
            f"{DEFAULT_API_BASE}/repos/{owner}/{repo}/discussions/{number}", token=token
        )
    except Exception:
        # Minimal fallback
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
