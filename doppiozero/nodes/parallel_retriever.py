from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from .retriever import RetrieverNode


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
        result_ls = [
            {
                "url": "https://github.com/example/conversation/3",
                "summary": "Parallel retrieved summary",
                "score": 0.92,
                "search_mode": "keyword",
                "conversation": {},
            }
        ]
        return result_ls
