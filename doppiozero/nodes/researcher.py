from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..contents import content_manager, content_fetcher

logger = get_logger(__name__)


class InitialResearchNode(Node):
    """Node that performs the initial semantic research for a request.

    Parameters
    ----------
    None

    Attributes
    ----------
    logger : logging.Logger
        Module-level logger obtained via :func:`doppiozero.utils.utils.get_logger`.
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.

    Notes
    -----
    This node seeds shared memory with initial ``hits``, ``notes``, and
    ``search_queries`` derived from the user's request.

    """

    def prep(self, shared):
        """Create an initial search plan from the user's request.

        Args:
            shared : Shared flow state. Expected to contain the key ``request``.

        Returns:
            A search plan dictionary with a ``query`` key derived from the user's request.

        """
        logger.info("=== INITIAL RESEARCH PHASE ===")
        logger.info("Starting initial semantic search for: %s", shared.get("request"))
        # Preserve shared for exec to access configuration like collection, cache_path, etc.
        self.shared = shared
        return {"query": shared.get("request")}

    def exec(self, plan):
        """Run the initial semantic search plan and return results.

        Args:
            plan : a search plan produced by :meth:`prep`.

        Returns:
            A list of retrieved conversation dictionaries.

        """
        logger.info("Executing initial semantic search and enriching results...")
        shared = getattr(self, "shared", {}) or {}

        request = plan.get("query") or shared.get("request") or ""
        collection = shared.get("collection")
        limit = int(shared.get("top_k", 5))
        max_depth = int(shared.get("max_depth", 1))
        cache_path = shared.get("cache_path")
        # Support an optional executive summary prompt path in shared
        prompt_path = shared.get("executive_summary_prompt_path") or shared.get("prompt_path")

        all_hit_ls = []

        for depth in range(max_depth):
            q = f"{request} (pass {depth+1})"
            logger.info("Searching (pass %d): %s", depth + 1, q)
            try:
                result_ls = content_manager.search(q, max_results=limit) or []
            except Exception as e:
                logger.warning("Search failed on pass %d for query '%s': %s", depth + 1, q, e)
                continue

            for r in result_ls:
                url = r.get("url")
                if not url:
                    continue
                logger.info("Fetching conversation: %s", url)
                try:
                    convo_dc = content_fetcher.fetch_github_conversation(url, cache_path=cache_path)
                except Exception as e:
                    logger.warning("Fetch failed for %s: %s", url, e)
                    continue

                summary = ""
                try:
                    if prompt_path:
                        summary = content_manager.summarize(url, prompt_path, cache_path=cache_path)
                    else:
                        summary = f"Summary for {url} (no prompt provided)"
                except Exception as e:
                    logger.warning("Summary failed for %s: %s", url, e)

                hit_dc = {
                    "url": url,
                    "summary": summary,
                    "score": r.get("score", 0.9),
                    "conversation": convo_dc,
                }
                all_hit_ls.append(hit_dc)

                # Optionally upsert to vector DB
                try:
                    if collection:
                        content_manager.vector_upsert(
                            summary or url,
                            collection,
                            {"url": url},
                            model=shared.get("models", {}).get("embed"),
                        )
                except Exception as e:
                    logger.warning("Vector upsert failed for %s: %s", url, e)

        # Initialize shared memory structure expected by downstream nodes
        shared["memory"] = {
            "hits": all_hit_ls,
            "notes": [],
            "search_queries": [request],
        }
        logger.info("\u2713 Initial research complete: %d conversations collected", len(all_hit_ls))
        return all_hit_ls

    def post(self, shared, prep_res, exec_res):
        """Store initial research results into shared memory.

        This initializes the shared memory structure with collected hits, notes,
        and the search query history.

            Args:
                shared : Shared flow state.
                prep_res : The search plan returned by :meth:`prep`.
                exec_res : The results returned by :meth:`exec`.

            Returns:
                None

        """
        shared["memory"] = {
            "hits": exec_res,
            "notes": [],
            "search_queries": [shared["request"]],
        }
        logger.info(f"\u2713 Initial research complete: {len(exec_res)} conversations collected")
        return None
