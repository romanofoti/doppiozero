"""Light adapter over PyGithub to provide simple normalized dicts for the rest of the
codebase.

This module centralizes GitHub API usage via PyGithub and returns simple dict
structures matching the shapes used elsewhere in the repository.
"""

from typing import Optional, Dict, Any, List
import os

try:
    from github import Github
    from github.Issue import Issue
    from github.PullRequest import PullRequest
except Exception as e:
    Github = None  # type: ignore


def get_client(token: Optional[str] = None):
    token = token or os.environ.get("GITHUB_TOKEN")
    if Github is None:
        raise ImportError("PyGithub is not installed")
    if token:
        return Github(token)
    return Github()


def _normalize_user(u) -> Optional[str]:
    if not u:
        return None
    return getattr(u, "login", None)


def _normalize_comment(c) -> Dict[str, Any]:
    return {
        "author": _normalize_user(getattr(c, "user", None)),
        "body": getattr(c, "body", None),
        "created_at": (
            getattr(c, "created_at", None).isoformat() if getattr(c, "created_at", None) else None
        ),
        "updated_at": (
            getattr(c, "updated_at", None).isoformat() if getattr(c, "updated_at", None) else None
        ),
        "url": getattr(c, "html_url", None) or getattr(c, "url", None),
    }


def fetch_issue(owner: str, repo: str, number: str, token: Optional[str] = None) -> Dict[str, Any]:
    gh = get_client(token)
    repository = gh.get_repo(f"{owner}/{repo}")
    issue = repository.get_issue(int(number))  # type: ignore

    comments = [_normalize_comment(c) for c in issue.get_comments()]

    normalized = {
        "type": "issue",
        "url": getattr(issue, "html_url", None),
        "owner": owner,
        "repo": repo,
        "number": int(number),
        "title": getattr(issue, "title", None),
        "body": getattr(issue, "body", None),
        "user": _normalize_user(getattr(issue, "user", None)),
        "state": getattr(issue, "state", None),
        "created_at": (
            getattr(issue, "created_at", None).isoformat()
            if getattr(issue, "created_at", None)
            else None
        ),
        "updated_at": (
            getattr(issue, "updated_at", None).isoformat()
            if getattr(issue, "updated_at", None)
            else None
        ),
        "comments": comments,
    }
    return normalized


def fetch_pr(owner: str, repo: str, number: str, token: Optional[str] = None) -> Dict[str, Any]:
    gh = get_client(token)
    repository = gh.get_repo(f"{owner}/{repo}")
    pr = repository.get_pull(int(number))  # type: ignore

    comments = [_normalize_comment(c) for c in pr.get_issue_comments()]
    reviews = [
        {
            "author": _normalize_user(getattr(r, "user", None)),
            "body": getattr(r, "body", None),
            "state": getattr(r, "state", None),
            "submitted_at": (
                getattr(r, "submitted_at", None).isoformat()
                if getattr(r, "submitted_at", None)
                else None
            ),
        }
        for r in pr.get_reviews()
    ]
    review_comments = [_normalize_comment(c) for c in pr.get_review_comments()]
    commits = [
        {
            "sha": getattr(c, "sha", None),
            "message": (
                getattr(c, "commit", {}).get("message") if getattr(c, "commit", None) else None
            ),
            "url": getattr(c, "html_url", None) or getattr(c, "url", None),
        }
        for c in pr.get_commits()
    ]

    # Diff: PyGithub doesn't provide diff content directly; request via API URL
    diff = None
    try:
        diff = gh._requester.requestJsonAndCheck(
            "GET", pr.url, headers={"Accept": "application/vnd.github.v3.diff"}
        )[2]
    except Exception:
        diff = None

    normalized = {
        "type": "pull_request",
        "url": getattr(pr, "html_url", None),
        "owner": owner,
        "repo": repo,
        "number": int(number),
        "title": getattr(pr, "title", None),
        "body": getattr(pr, "body", None),
        "user": _normalize_user(getattr(pr, "user", None)),
        "state": getattr(pr, "state", None),
        "created_at": (
            getattr(pr, "created_at", None).isoformat() if getattr(pr, "created_at", None) else None
        ),
        "updated_at": (
            getattr(pr, "updated_at", None).isoformat() if getattr(pr, "updated_at", None) else None
        ),
        "comments": comments,
        "reviews": reviews,
        "review_comments": review_comments,
        "commits": commits,
        "diff": diff,
    }
    return normalized


def fetch_discussion(
    owner: str, repo: str, number: str, token: Optional[str] = None
) -> Dict[str, Any]:
    # PyGithub may not expose discussions in all versions; attempt to call via REST
    gh = get_client(token)
    try:
        # Use the REST API endpoint for discussions
        path = f"/repos/{owner}/{repo}/discussions/{number}"
        data = gh._requester.requestJsonAndCheck("GET", path)[2]
        # Normalize minimal fields
        return {
            "type": "discussion",
            "url": data.get("html_url")
            or f"https://github.com/{owner}/{repo}/discussions/{number}",
            "owner": owner,
            "repo": repo,
            "number": int(number),
            "body": data.get("body"),
            "updated_at": data.get("updated_at"),
        }
    except Exception:
        return {"url": f"https://github.com/{owner}/{repo}/discussions/{number}", "number": number}


def search_issues(
    query: str, max_results: int = 50, token: Optional[str] = None
) -> List[Dict[str, Any]]:
    gh = get_client(token)
    # Use the search_issues API
    q = query
    results = gh.search_issues(q)  # type: ignore
    out = []
    count = 0
    for it in results:
        if count >= max_results:
            break
        out.append(
            {
                "url": getattr(it, "html_url", None),
                "updated_at": (
                    getattr(it, "updated_at", None).isoformat()
                    if getattr(it, "updated_at", None)
                    else None
                ),
            }
        )
        count += 1
    return out
