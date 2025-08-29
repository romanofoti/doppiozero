from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..contents import content_manager

logger = get_logger(__name__)


class RetrieverNode(Node):
    """A node that performs retrieval/search operations and records results.

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.
    """

    def prep(self, shared):
        """Prepare the retrieval phase by returning the next search plans.

        This method is called before execution. It typically inspects the
        shared state and returns a list of search plans that the
        ``exec`` method will process.

        Args:
            shared : the shared flow state containing keys like ``next_search_plans``.

        Returns:
            A list of search plan dicts to execute. If none are present, an empty list is returned.

        """
        logger.info("=== RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        """Execute the search plans and return retrieved conversation summaries.

        This method performs the actual retrieval (e.g. semantic or keyword
        search) and returns a list of result dicts. Each result dict should
        include at least ``url``, ``summary``, and ``score``.

        Args:
            search_plans : a list of search plan dicts produced by :meth:`prep`.

        Returns:
            A list of result dictionaries describing retrieved conversations.

        """
        logger.info("Executing search operations and retrieving data...")
        result_ls = []
        for plan in search_plans:
            query = plan.get("query") or plan.get("q")
            collection = plan.get("collection") or plan.get("index") or "default"
            qdrant_url = plan.get("qdrant_url")
            top_k = int(plan.get("top_k", 5))
            try:
                hit_ls = content_manager.vector_search(query, collection, qdrant_url, top_k)
                result_ls.extend(hit_ls)
            except Exception as e:
                logger.error("Error during vector_search for plan %s: %s", plan, e)
        return result_ls

    def post(self, shared, prep_res, exec_res):
        """Post-process retrieved results and update shared memory.

        This method stores the execution results into the shared memory
        structure, updates search query history, and advances the depth
        counter for the flow.

        Args:
            shared : the shared state dictionary used across nodes.
            prep_res : the preparation result returned by :meth:`prep`.
            exec_res : the execution result returned by :meth:`exec`.

        Returns:
            A control token for the flow: "continue" to keep iterating or
            "final" to stop when max depth is reached.

        """
        shared["memory"]["hits"].extend(exec_res)
        shared["memory"]["search_queries"].append(", ".join([plan["query"] for plan in prep_res]))
        logger.info(f"Added {len(exec_res)} new conversations to memory.")
        shared["current_depth"] = shared.get("current_depth", 0) + 1
        if shared["current_depth"] < shared["max_depth"]:
            return "continue"
        else:
            return "final"
