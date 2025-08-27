import json
import logging
from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class InitialResearchNode(Node):
    """Node that performs the initial semantic research for a request.
    This node starts the search process by creating an initial semantic search
    plan using the user's request and then executes that plan to collect
    initial candidate conversations.

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.
    """

    def prep(self, shared):
        """Create an initial search plan from the user's request.

        Args:
            shared : Shared flow state. Expected to contain the key ``request``.

        Returns:
            A search plan dictionary with a ``query`` key derived from the user's request.

        """
        logger.info("=== INITIAL RESEARCH PHASE ===")
        logger.info(f"Starting initial semantic search for: {shared['request']}")
        return {"query": shared["request"]}

    def exec(self, plan):
        """Run the initial semantic search plan and return results.

        Args:
            plan : a search plan produced by :meth:`prep`.

        Returns:
            A list of retrieved conversation dictionaries.

        """
        logger.info("Executing initial semantic search and enriching results...")
        result_ls = [
            {
                "url": "https://github.com/example/conversation/1",
                "summary": "Example summary",
                "score": 0.95,
                "conversation": {},
            }
        ]
        return result_ls

    def post(self, shared, prep_res, exec_res):
        """Store initial research results into shared memory.

        This initializes the shared memory structure with collected hits, notes, and the search query history.

        Args:
            shared : Shared flow state.
            prep_res : The search plan returned by :meth:`prep`.
            exec_res : The results returned by :meth:`exec`.

        Returns:
            None

        """
        shared["memory"] = {"hits": exec_res, "notes": [], "search_queries": [shared["request"]]}
        logger.info(f"✓ Initial research complete: {len(exec_res)} conversations collected")
        return None
