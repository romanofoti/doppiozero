"""
Light adapter over PyGithub providing simple normalized dicts for the rest of
the codebase. This module centralizes GitHub API usage and returns plain
structures matching the shapes used elsewhere in the repository.
"""

from typing import Optional, Dict, Any, List
import os

from github import Github

from ..utils.utils import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """
    Light adapter over PyGithub providing normalized dictionaries for issues, PRs and discussions.

    Parameters
    ----------
    token : Optional[str]
        Optional GitHub API token. Falls back to the GITHUB_TOKEN environment
        variable when not provided.

    Attributes
    ----------
    gh : github.Github
        The underlying PyGithub client instance.
    """

    def __init__(self, token: Optional[str] = None):
        """Initialize the GitHub client adapter with an optional token.

        Args:
            token : Optional GitHub API token; falls back to GITHUB_TOKEN env var.

        Returns:
            None

        """
        token = token or os.environ.get("GITHUB_TOKEN")
        if token:
            logger.info("Using GitHub API token ending with %s", token[-4:])
            self.gh = Github(token)
        else:
            raise ValueError("GitHub API token is required")

    def _normalize_user(self, u) -> Optional[str]:
        """Normalize a PyGithub user object to a login string.

        Args:
            u : A PyGithub user object or None.

        Returns:
            The user's login string or None.

        """
        if not u:
            return None
        return getattr(u, "login", None)

    def _normalize_comment(self, c) -> Dict[str, Any]:
        """Normalize a comment object to a plain dictionary.

        Args:
            c : A PyGithub comment-like object.

        Returns:
            A dictionary with keys: author, body, created_at, updated_at, url.

        """
        return {
            "author": self._normalize_user(getattr(c, "user", None)),
            "body": getattr(c, "body", None),
            "created_at": (
                getattr(c, "created_at", None).isoformat()
                if getattr(c, "created_at", None)
                else None
            ),
            "updated_at": (
                getattr(c, "updated_at", None).isoformat()
                if getattr(c, "updated_at", None)
                else None
            ),
            "url": getattr(c, "html_url", None) or getattr(c, "url", None),
        }

    def fetch_issue(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        """Fetch an issue and return a normalized dictionary representation.

        Args:
            owner : Repository owner/login.
            repo : Repository name.
            number : Issue number (as string or int).

        Returns:
            A dictionary with normalized issue fields (url, title, body, comments, etc.).

        """
        repository = self.gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(int(number))  # type: ignore

        comment_ls = [self._normalize_comment(c) for c in issue.get_comments()]

        normalized_dc = {
            "type": "issue",
            "url": getattr(issue, "html_url", None),
            "owner": owner,
            "repo": repo,
            "number": int(number),
            "title": getattr(issue, "title", None),
            "body": getattr(issue, "body", None),
            "user": self._normalize_user(getattr(issue, "user", None)),
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
            "comments": comment_ls,
        }
        return normalized_dc

    def fetch_pr(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        """Fetch a pull request and return a normalized dictionary representation.

        Args:
            owner : Repository owner/login.
            repo : Repository name.
            number : Pull request number (as string or int).

        Returns:
            A dictionary with normalized pull request fields. Includes keys such as
            url, title, body, reviews, commits and diff when available.

        """
        repository = self.gh.get_repo(f"{owner}/{repo}")
        pr = repository.get_pull(int(number))  # type: ignore

        comment_ls = [self._normalize_comment(c) for c in pr.get_issue_comments()]
        review_ls = [
            {
                "author": self._normalize_user(getattr(r, "user", None)),
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
        review_comment_ls = [self._normalize_comment(c) for c in pr.get_review_comments()]
        commit_ls = []
        for c in pr.get_commits():
            commit_obj = getattr(c, "commit", None)
            commit_message = commit_obj.get("message") if commit_obj else None
            commit_ls.append(
                {
                    "sha": getattr(c, "sha", None),
                    "message": commit_message,
                    "url": getattr(c, "html_url", None) or getattr(c, "url", None),
                }
            )

        # PyGithub doesn't provide diff content directly. Request via REST
        # endpoint and accept diff media type when possible.
        diff = None
        try:
            # Request the PR diff via the REST endpoint and accept diff media type
            diff = self.gh._requester.requestJsonAndCheck(
                "GET",
                pr.url,
                headers={"Accept": "application/vnd.github.v3.diff"},
            )[2]
        except Exception:
            diff = None

        normalized_dc = {
            "type": "pull_request",
            "url": getattr(pr, "html_url", None),
            "owner": owner,
            "repo": repo,
            "number": int(number),
            "title": getattr(pr, "title", None),
            "body": getattr(pr, "body", None),
            "user": self._normalize_user(getattr(pr, "user", None)),
            "state": getattr(pr, "state", None),
            "created_at": (
                getattr(pr, "created_at", None).isoformat()
                if getattr(pr, "created_at", None)
                else None
            ),
            "updated_at": (
                getattr(pr, "updated_at", None).isoformat()
                if getattr(pr, "updated_at", None)
                else None
            ),
            "comments": comment_ls,
            "reviews": review_ls,
            "review_comments": review_comment_ls,
            "commits": commit_ls,
            "diff": diff,
        }
        return normalized_dc

    def fetch_discussion(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
        """Fetch a discussion via REST fallback and return a normalized dict.

        Args:
            owner : Repository owner/login.
            repo : Repository name.
            number : Discussion number (as string or int).

        Returns:
            A dictionary with normalized discussion fields, or a minimal fallback
            dict on error.

        """
        # Attempt to call via REST
        try:
            path = f"/repos/{owner}/{repo}/discussions/{number}"
            data = self.gh._requester.requestJsonAndCheck("GET", path)[2]
            url = data.get("html_url") or (
                f"https://github.com/{owner}/{repo}/discussions/{number}"
            )
            return {
                "type": "discussion",
                "url": url,
                "owner": owner,
                "repo": repo,
                "number": int(number),
                "body": data.get("body"),
                "updated_at": data.get("updated_at"),
            }
        except Exception:
            return {
                "url": f"https://github.com/{owner}/{repo}/discussions/{number}",
                "number": number,
            }

    def search_issues(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search issues/PRs/discussions using a GitHub search query.

        Args:
            query : The GitHub search query string.
            max_results : Maximum number of results to return.

        Returns:
            A list of minimal dicts containing url and updated_at for each match.

        """
        results = self.gh.search_issues(query)  # type: ignore
        out_ls: List[Dict[str, Any]] = []
        count = 0
        for it in results:
            if count >= max_results:
                break
            out_ls.append(
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
        return out_ls
