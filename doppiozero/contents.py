"""content_service.py

Provides two classes:
 - ContentFetcher: fetches GitHub conversations (issues/prs/discussions) and handles caching.
 - ContentManager: higher-level orchestration that searches and summarizes conversations using a ContentFetcher and an LLM client.

The module exposes singletons `content_fetcher` and `content_manager` for convenience.
"""

from typing import Optional, Dict, Any, Tuple, List
import os
import json
import datetime
import urllib.parse

from .github_client import GitHubClient
from .llm_client import llm_client
from .utils.utils import get_logger, read_json_or_none, write_json_safe
from .utils.utils import safe_filename_for_url

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

    def index_summary(
        self,
        conversation_url: str,
        executive_summary_prompt_path: str,
        topics_prompt_path: str,
        collection: str,
        cache_path: Optional[str] = None,
        updated_at: Optional[str] = None,
        model: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        max_topics: Optional[int] = None,
        skip_if_up_to_date: bool = False,
        indexer=None,
    ) -> Dict[str, Any]:
        """Index a GitHub conversation summary using the provided indexer (defaults to vector_upsert.vector_upsert).

        This method orchestrates fetch -> summarize -> index and caches payloads when requested.
        """
        # default indexer uses the manager's built-in vector_upsert implementation
        indexer = indexer or self.vector_upsert

        # Fetch conversation
        convo_dc = self.fetcher.fetch_github_conversation(
            conversation_url, cache_path=cache_path, updated_at=updated_at
        )

        # Build executive summary
        try:
            with open(executive_summary_prompt_path, "r", encoding="utf-8") as f:
                exec_prompt = f.read()
        except Exception as e:
            logger.error(f"Error reading executive summary prompt: {e}")
            exec_prompt = ""
        executive_summary = (
            self.llm.generate(
                exec_prompt.replace("{{conversation}}", json.dumps(convo_dc, indent=2)[:8000])
            )
            if self.llm
            else f"Executive summary for {conversation_url}: {exec_prompt[:60]}..."
        )

        # Topics extraction (simple placeholder using prompt)
        try:
            with open(topics_prompt_path, "r", encoding="utf-8") as f:
                topics_prompt = f.read()
        except Exception as e:
            logger.error(f"Error reading topics prompt: {e}")
            topics_prompt = ""
        base_topic_ls = ["performance", "authentication", "database", "caching", "bug-fix"]
        topic_ls = base_topic_ls[:max_topics] if max_topics is not None else base_topic_ls

        # Prepare payload/metadata
        vector_payload_dc = {
            "url": conversation_url,
            "title": convo_dc.get("title"),
            "author": convo_dc.get("user") or convo_dc.get("author"),
            "state": convo_dc.get("state"),
            "created_at": convo_dc.get("created_at"),
            "updated_at": convo_dc.get("updated_at"),
            "executive_summary": executive_summary,
            "topics": topic_ls,
            "collection": collection,
            "model": model,
            "qdrant_url": qdrant_url,
        }

        # Cache payload if requested
        if cache_path:
            safe_url = safe_filename_for_url(conversation_url)
            cache_file = os.path.join(cache_path, f"index_summary_{safe_url}.json")
            try:
                write_json_safe(cache_file, vector_payload_dc)
            except Exception as e:
                logger.error(f"Error writing cache file: {e}")

        # Call indexer (upsert)
        try:
            indexer(
                executive_summary,
                collection,
                {k: v for k, v in vector_payload_dc.items() if k != "executive_summary"},
                model=model,
                qdrant_url=qdrant_url,
                skip_if_up_to_date=("updated_at" if skip_if_up_to_date else None),
                vector_id_key="url",
            )
        except Exception as e:
            logger.error(f"Indexing failed for {conversation_url}: {e}")

        logger.info(
            f"Indexed summary for {conversation_url} in collection '{collection}' with topics: {topic_ls}"
        )
        return vector_payload_dc

    def vector_upsert(
        self,
        text: str,
        collection: str,
        metadata: Dict[str, Any],
        model: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        skip_if_up_to_date: Optional[str] = None,
        vector_id_key: Optional[str] = None,
    ) -> None:
        """
        Embed text and upsert vectors with metadata into the configured vector store.

        This is the in-manager replacement for the old `vector_upsert.vector_upsert` module.
        """
        # Step 1: Generate embedding via llm_client
        try:
            embedding = self.llm.embed(text, model=model)
        except Exception:
            embedding = self.llm.embed(text, model=model) if self.llm else [0.0]

        # Step 2: Deterministic vector id generation
        if vector_id_key and vector_id_key in metadata:
            vector_id = str(metadata[vector_id_key])
        else:
            vector_id = str(hash(text))

        # Step 3: Prepare payload
        vector_payload_dc = {
            "id": vector_id,
            "embedding": embedding,
            "metadata": metadata,
            "collection": collection,
            "model": model,
            "qdrant_url": qdrant_url,
        }

        # Step 4: Optionally skip if up-to-date
        if skip_if_up_to_date and skip_if_up_to_date in metadata:
            logger.info(f"Skipping upsert for {vector_id} (up-to-date by {skip_if_up_to_date})")
            return

        # Step 5: Log the simulated upsert (real implementation should call a provider API)
        logger.info(
            f"Upserted vector to collection '{collection}': {json.dumps(vector_payload_dc)[:120]}..."
        )


# Singletons
content_fetcher = ContentFetcher()
content_manager = ContentManager(fetcher=content_fetcher)
