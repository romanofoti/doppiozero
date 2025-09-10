import time
import random
import re
from typing import List

from duckduckgo_search import DDGS

from ...pocketflow import Node
from ...utils.utils import get_logger

logger = get_logger(__name__)


class SearcherNode(Node):
    """DuckDuckGo-backed search node with rate-limit mitigation and query hygiene."""

    _ddgs = None  # persistent client
    _recent_queries: List[str] = []
    _recent_queries_max = 20

    def prep(self, shared):
        """Capture shared for later use and return the raw search query."""
        self._shared = shared
        return shared["search_query"]

    @classmethod
    def _get_ddgs(cls):
        if cls._ddgs is None:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            }
            cls._ddgs = DDGS(headers=headers)
        return cls._ddgs

    @staticmethod
    def _normalize_query(q: str) -> str:
        q = q.strip().strip('"')
        words = []
        seen = set()
        for w in re.split(r"\s+", q):
            lw = w.lower()
            if lw not in seen:
                seen.add(lw)
                words.append(w)
        norm = " ".join(words)
        if len(norm) > 140:
            norm = norm[:140]
        return norm

    @classmethod
    def _record_query(cls, q: str):
        cls._recent_queries.append(q)
        if len(cls._recent_queries) > cls._recent_queries_max:
            cls._recent_queries = cls._recent_queries[-cls._recent_queries_max :]

    @classmethod
    def _is_duplicate(cls, q: str) -> bool:
        return q in cls._recent_queries

    def _search_web(self, query):
        ddgs = self._get_ddgs()
        norm_query = self._normalize_query(query)
        if self._is_duplicate(norm_query):
            logger.info("🔁 Skipping duplicate search query (cached this run).")
            return ""

        backoff = 1.0
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                results = list(ddgs.text(norm_query, backend="lite", max_results=3))
                self._record_query(norm_query)
                results_str_parts = []
                for r in results:
                    title = r.get("title", "")
                    href = r.get("href", "")
                    body = r.get("body", "")
                    results_str_parts.append(f"Title: {title}\nURL: {href}\nSnippet: {body}")
                results_str = "\n\n".join(results_str_parts)
                return results_str
            except Exception as exc:  # pragma: no cover
                msg = str(exc)
                if attempt == attempts:
                    logger.warning(
                        f"⚠️ Search failed after {attempts} attempts (last error: {msg}). Proceeding with empty results."  # noqa: E501
                    )
                    return ""
                sleep_for = backoff + random.uniform(0, 0.4)
                logger.info(
                    f"⏳ Rate limited or error (attempt {attempt}/{attempts}): {msg}. Backing off {sleep_for:.2f}s..."  # noqa: E501
                )
                time.sleep(sleep_for)
                backoff *= 2
            except Exception as exc:  # pragma: no cover
                logger.warning(f"⚠️ Unexpected search error: {exc}")
                return ""
        return ""

    def exec(self, search_query):
        """Search the web for the given query."""
        logger.info(f"🌐 Searching the web for: {search_query}")
        results = self._search_web(search_query)
        return results

    def post(self, shared, prep_res, exec_res):
        """Save the search results and go back to the decision node."""
        # Add the search results to the context in the shared store
        previous = shared.get("context", "")
        shared["context"] = (
            previous + "\n\nSEARCH: " + shared["search_query"] + "\nRESULTS: " + exec_res
        )

        logger.info("📚 Found information, analyzing results...")

        # Always go back to the decision node after searching
        return "decide"
