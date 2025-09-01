from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class ContextCompacterNode(Node):
    """Node that compacts conversation/context to satisfy LLM limits.

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
    The node stores the compacted context back into shared state and
    increments ``compaction_attempts`` to allow the flow to track retries.

    """

    def prep(self, shared):
        """Return the current memory/context to be compacted.

        Args:
            shared : Shared state containing ``memory`` which holds conversation data.

        Returns:
            The current memory/context structure.

        """
        logger.info("=== CONTEXT COMPACTION PHASE ===")
        return shared.get("memory", {})

    def exec(self, context):
        """Perform compaction of the provided context.

        Args:
            context : The memory/context to compact.

        Returns:
            The compacted memory/context.

        """
        logger.info("Compacting context for LLM constraints...")
        return context

    def post(self, shared, prep_res, exec_res):
        """Store the compacted context back to shared memory and increment attempt counter.

        Args:
            shared : Shared flow state to update.
            prep_res : The original memory/context returned by :meth:`prep`.
            exec_res : The compacted memory/context returned by :meth:`exec`.

        Returns:
            A control token indicating next action (e.g., "retry").

        """
        shared["memory"] = exec_res
        shared["compaction_attempts"] = shared.get("compaction_attempts", 0) + 1
        logger.info("Context compaction complete.")
        return "retry"
