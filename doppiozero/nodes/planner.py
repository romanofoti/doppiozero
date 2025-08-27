from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class PlannerNode(Node):
    """Node responsible for creating search plans from a request.

    The planner translates a user's request into one or more search queries
    targeting different tools (semantic, keyword, etc.).

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.
    """

    def prep(self, shared):
        """Build initial query templates based on the user's request.

        Args:
            shared : Shared flow state. Expected to include ``request``.

        Returns:
            A dictionary with query templates for different search tools.

        """
        logger.info("=== PLANNING PHASE ===")
        return {
            "semantic": {"query": shared["request"] + " implementation details"},
            "keyword": {"query": "repo:example is:issue"},
        }

    def exec(self, plan):
        """Transform query templates into executable search plans.

        Args:
            plan : The query templates produced by :meth:`prep`.

        Returns:
            A list of search plan dicts each containing a ``tool`` and ``query``.

        """
        logger.info("Transforming queries into search plans...")
        return [
            {"tool": "semantic", "query": plan["semantic"]["query"]},
            {"tool": "keyword", "query": plan["keyword"]["query"]},
        ]

    def post(self, shared, prep_res, exec_res):
        """Store generated search plans into the shared flow state.

        Args:
            shared : Shared flow state to update.
            prep_res : The templates returned by :meth:`prep`.
            exec_res : The list of search plans returned by :meth:`exec`.

        Returns:
            None

        """
        shared["next_search_plans"] = exec_res
        logger.info(f"✓ Planning complete, generated {len(exec_res)} search plans")
        return None
