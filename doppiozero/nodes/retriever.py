from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..contents import content_manager
from typing import List, Dict, Any
import os

logger = get_logger(__name__)


class RetrieverNode(Node):
    """Perform iterative retrieval/search over GitHub conversations and record results.

    This node executes one retrieval iteration per invocation. It supports both
    semantic (vector) and keyword search modes, enriches the raw hits with
    conversation bodies and generated summaries, deduplicates results across
    iterations, and records per-iteration research notes.

    Enhanced behavior:
    - Semantic hits enriched with conversation bodies (``fetch_conversation=True``)
    - Generates missing summaries using an executive summary prompt if provided
    - Deduplicates by URL in :meth:`post` (upgrading blank summaries / conversations)
    - Records per-iteration research notes (parity with upstream Ruby implementation)
    - Continues deep-research only when new unique conversations are added

    Expected shared state keys (read / mutated):
    - ``shared['memory']``: ``{'hits': [...], 'notes': [...], 'search_queries': [...]}``
        - ``shared['executive_summary_prompt_path']`` | ``shared['prompt_path']``: Optional summary
            prompt path.
    - ``shared['cache_path']``: Optional cache directory.
    - ``shared['collection']``: Default semantic vector collection name.

    Returns (routing):
    - ``continue`` token when further retrieval iterations should run.
    - ``final`` token when depth exhausted or no new unique hits were added.
    """

    def prep(self, shared):
        """Return the list of search plan dictionaries for this iteration.

        Parameters
        ----------
        shared : Dict[str, Any]
            The shared flow state containing (optionally) ``next_search_plans``.

        Returns
        -------
        List[Dict[str, Any]]
            List of search plan dicts. Empty when no further retrieval is scheduled.
        """
        logger.info("=== RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plan_ls):  # type: ignore[override]
        """Execute search plans, enrich results, and return the enriched list.

        Workflow Steps
        --------------
        1. Perform semantic or keyword retrieval.
        2. Fetch conversation bodies for semantic results.
        3. Generate summaries for items missing one when a summary prompt exists.
        4. Tag each result with its originating search mode.

        Parameters
        ----------
        search_plan_ls : List[Dict[str, Any]]
            The list of search plan dictionaries returned from :meth:`prep`.

        Returns
        -------
        List[Dict[str, Any]]
            Enriched result dictionaries (may be empty when no plans provided).
        """
        logger.info("Executing search operations and retrieving data...")
        enriched_result_ls: List[Dict[str, Any]] = []

        if not search_plan_ls:
            logger.info("No search plans provided to RetrieverNode.exec")
            return enriched_result_ls

        shared = getattr(self, "shared", {}) or {}
        cache_path = shared.get("cache_path")
        summary_prompt_path = shared.get("executive_summary_prompt_path") or shared.get(
            "prompt_path"
        )
        collection_default = shared.get("collection") or os.environ.get("DEFAULT_COLLECTION")

        for plan in search_plan_ls:
            tool = plan.get("tool") or plan.get("type") or "semantic"
            query = plan.get("query") or plan.get("q") or plan.get("q_str") or ""
            collection = plan.get("collection") or plan.get("index") or collection_default
            top_k = int(plan.get("top_k", plan.get("limit", 5)))

            if tool == "semantic":
                try:
                    hit_ls = (
                        content_manager.vector_search(
                            query,
                            collection=collection,
                            top_k=top_k,
                            fetch_conversation=True,
                            cache_path=cache_path,
                        )
                        or []
                    )
                except Exception as e:
                    logger.warning("Semantic vector_search failed: %s", e)
                    hit_ls = []
                for h in hit_ls:
                    h.setdefault("search_mode", "semantic")
                    if (not h.get("summary")) and summary_prompt_path and h.get("url"):
                        try:
                            generated = content_manager.summarize(
                                h["url"], summary_prompt_path, cache_path=cache_path
                            )
                            if generated:
                                h["summary"] = generated
                        except Exception as se:
                            logger.debug("Failed to summarize %s: %s", h.get("url"), se)
                    enriched_result_ls.append(h)
                continue

            if tool == "keyword":
                try:
                    if hasattr(content_manager, "github_search"):
                        raw_hit_ls = content_manager.github_search(query, max_results=top_k) or []
                    else:
                        raw_hit_ls = content_manager.search(query, max_results=top_k) or []
                except Exception as e:
                    logger.warning("Keyword search failed: %s", e)
                    raw_hit_ls = []
                for r in raw_hit_ls:
                    url = r.get("url") or r.get("html_url")
                    if not url:
                        continue
                    summary_txt = r.get("summary") or r.get("title") or ""
                    convo_dc: Dict[str, Any] = {}
                    try:
                        convo_dc = content_manager.fetcher.fetch_github_conversation(
                            url, cache_path=cache_path
                        )
                    except Exception as fe:
                        logger.debug("Conversation fetch failed for %s: %s", url, fe)
                    if (not summary_txt) and summary_prompt_path:
                        try:
                            summary_txt = content_manager.summarize(
                                url, summary_prompt_path, cache_path=cache_path
                            )
                        except Exception as se:
                            logger.debug("Failed to summarize keyword result %s: %s", url, se)
                    enriched_result_ls.append(
                        {
                            "url": url,
                            "summary": summary_txt,
                            "score": r.get("score", 0.0),
                            "search_mode": "keyword",
                            "conversation": convo_dc,
                        }
                    )
                continue

            # Fallback unknown tool
            try:
                fallback_hit_ls = content_manager.search(query, max_results=top_k) or []
            except Exception as e:
                logger.warning("Unknown tool search failed for '%s': %s", query, e)
                fallback_hit_ls = []
            for r in fallback_hit_ls:
                url = r.get("url")
                if not url:
                    continue
                enriched_result_ls.append(
                    {
                        "url": url,
                        "summary": r.get("title") or r.get("summary") or "",
                        "score": r.get("score", 0.0),
                        "search_mode": tool,
                        "conversation": {},
                    }
                )

        return enriched_result_ls

    def post(self, shared, prep_res, exec_res):
        """Deduplicate, upgrade, note progress, and decide routing token.

        Parameters
        ----------
        shared : Dict[str, Any]
            Shared flow state (mutated in-place).
        prep_res : List[Dict[str, Any]]
            Search plan dicts executed in this iteration.
        exec_res : List[Dict[str, Any]]
            Enriched retrieval results produced by :meth:`exec`.

        Returns
        -------
        str
            ``continue`` when another iteration should run, else ``final``.
        """
        memory_dc = shared.setdefault("memory", {})
        hits_ls = memory_dc.setdefault("hits", [])
        search_queries_ls = memory_dc.setdefault("search_queries", [])
        notes_ls = memory_dc.setdefault("notes", [])

        existing_by_url_dc: Dict[str, Dict[str, Any]] = {}
        for hit_dc in hits_ls:
            url = hit_dc.get("url")
            if url:
                existing_by_url_dc[url] = hit_dc

        new_unique_count = 0
        for new_hit_dc in exec_res or []:
            url = new_hit_dc.get("url")
            if not url:
                continue
            existing_dc = existing_by_url_dc.get(url)
            if not existing_dc:
                hits_ls.append(new_hit_dc)
                existing_by_url_dc[url] = new_hit_dc
                new_unique_count += 1
                continue
            upgraded = False
            if (not existing_dc.get("summary")) and new_hit_dc.get("summary"):
                existing_dc["summary"] = new_hit_dc["summary"]
                upgraded = True
            if (not existing_dc.get("conversation")) and new_hit_dc.get("conversation"):
                existing_dc["conversation"] = new_hit_dc.get("conversation")
                upgraded = True
            if upgraded:
                logger.debug("Upgraded existing hit for %s", url)

        executed_query_ls = [plan.get("query") for plan in prep_res if plan.get("query")]
        if executed_query_ls:
            search_queries_ls.append(", ".join(executed_query_ls))

        iteration_idx = shared.get("current_depth", 0) + 1
        note_str = (
            f"Iteration {iteration_idx}: executed {len(executed_query_ls)} queries; "
            f"added {new_unique_count} new unique conversations (total={len(hits_ls)})."
        )
        notes_ls.append(note_str)
        logger.info(note_str)

        shared["current_depth"] = shared.get("current_depth", 0) + 1
        if shared["current_depth"] < shared.get("max_depth", 0) and new_unique_count > 0:
            return "continue"
        return "final"
