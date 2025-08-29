from ..utils.utils import get_logger
from .retriever import RetrieverNode
from ..contents import content_manager


logger = get_logger(__name__)


class ParallelRetrieverNode(RetrieverNode):
    """A retriever node that performs parallel or batched retrieval.

    This node extends :class:`RetrieverNode` and is intended to run
    retrievals in parallel or in a batched fashion. It follows the same
    prep/exec/post lifecycle as RetrieverNode.

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`RetrieverNode`.
    """

    def prep(self, shared):
        """Prepare the parallel retrieval by returning search plans.

        Args:
            shared : Shared flow state. Expected to include ``next_search_plans``.

        Returns:
            The list of search plans to execute in parallel.

        """
        logger.info("=== PARALLEL RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        """Execute parallel search plans and return retrieved items.

        Args:
            search_plans : a list of search plan dictionaries.

        Returns:
            A list of result dictionaries produced by parallel retrieval.

        """
        logger.info("Executing parallel search operations...")
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
                logger.error("Error during parallel vector_search for plan %s: %s", plan, e)
        return result_ls
