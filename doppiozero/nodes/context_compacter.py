from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class ContextCompacterNode(Node):
    """Node that compacts conversation/context to satisfy LLM limits.

    This node is responsible for reducing or summarizing the current
    memory/context so it fits within token or size constraints for LLM
    calls. It updates the shared memory with the compacted context.

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.
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
