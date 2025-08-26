"""content_service.py

Provides two classes:
 - Fetcher: fetches GitHub conversations (issues/prs/discussions) and handles caching.
 - Manager: higher-level orchestration that searches and summarizes conversations using a Fetcher and an LLM client.

The module exposes singletons `fetcher` and `manager` for convenience.
"""

from typing import Optional, Dict, Any, Tuple, List
import os
import json
import datetime
import urllib.parse

from .github_client import GitHubClient
from .llm_client import llm_client
from .utils.utils import get_logger, read_json_or_none, write_json_safe
from .utils.scripts_common import safe_filename_for_url

logger = get_logger(__name__)


class ContentFetcher:
    """Fetch and cache GitHub conversation content."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def parse_content_info(self, input_str: str) -> Tuple[str, str, str, str]:
        input_str = input_str.strip()
        if input_str.startswith("http"):
            parts = urllib.parse.urlparse(input_str)
            path = parts.path.lstrip("/")
            segs = path.split("/")
            if len(segs) >= 4:
                owner, repo, type_, number = segs[0], segs[1], segs[2], segs[3]
                return owner, repo, type_, number
            raise ValueError(f"Unrecognized GitHub URL: {input_str}")
        segs = input_str.split("/")
        if len(segs) == 4:
            return segs[0], segs[1], segs[2], segs[3]
        raise ValueError(f"Unrecognized input: {input_str}")

    def _cache_path_for(
        self, cache_root: str, owner: str, repo: str, type_: str, number: str
    ) -> str:
        return os.path.join(cache_root, "conversations", owner, repo, type_, f"{number}.json")

    def _load_cache(self, path: str) -> Optional[Dict[str, Any]]:
        return read_json_or_none(path)

    def _save_cache(self, path: str, data: Dict[str, Any]) -> None:
        write_json_safe(path, data)

    def _get_updated_at(self, data: Dict[str, Any], type_: str) -> Optional[str]:
        if not data:
            return None
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

        # Fetch
        if type_ in ("issue", "issues"):
            data = self.fetch_issue(owner, repo, number)
        elif type_ in ("pull", "pulls", "pr", "prs"):
            data = self.fetch_pr(owner, repo, number)
        elif type_ in ("discussion", "discussions"):
            data = self.fetch_discussion(owner, repo, number)
        else:
            raise ValueError(f"Unknown conversation type: {type_}")

        # Updated at filter
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


class ContentManager:
    """High-level manager that searches and summarizes GitHub conversations."""

    def __init__(
        self, token: Optional[str] = None, llm=None, fetcher: Optional[ContentFetcher] = None
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.llm = llm or llm_client
        self.fetcher = fetcher or ContentFetcher()

    def search(self, query: str, max_results: int = 50):
        client = GitHubClient(self.token)
        results = client.search_issues(query, max_results=max_results)
        return results[:max_results]

    def summarize(
        self,
        conversation_url: str,
        executive_summary_prompt_path: str,
        cache_path: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> str:
        try:
            with open(executive_summary_prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read()
        except Exception as e:
            logger.error(f"Error reading executive summary prompt: {e}")
            return ""

        convo_dc = self.fetcher.fetch_github_conversation(
            conversation_url, cache_path=cache_path, updated_at=updated_at
        )
        convo_text = json.dumps(convo_dc, indent=2)[:8000]
        full_prompt = prompt.replace("{{conversation}}", convo_text).replace(
            "{{url}}", conversation_url
        )

        try:
            summary = self.llm.generate(full_prompt)
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            summary = f"Executive summary for {conversation_url}: {prompt[:120]}..."

        if cache_path:
            safe_url = safe_filename_for_url(conversation_url)
            cache_file = os.path.join(cache_path, f"summary_{safe_url}.json")
            try:
                write_json_safe(cache_file, {"summary": summary})
            except Exception as e:
                logger.error(f"Error writing cache file: {e}")

        return summary


# Singletons
content_fetcher = ContentFetcher()
content_manager = ContentManager(fetcher=content_fetcher)
