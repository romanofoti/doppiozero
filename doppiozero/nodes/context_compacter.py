from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..clients.llm import llm_client
from ..contents import content_manager
import os

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

        hits = context.get("hits", []) if isinstance(context, dict) else []
        # Configurable parameters
        max_hits = int(self.params.get("max_hits", 10))
        prompt_path = os.path.join(
            os.getcwd(), "prompts", "summarize", "github-conversation-executive-summary.md"
        )

        compacted = {**context}
        compacted_hits = []

        if not hits:
            return compacted

        if llm_client and os.path.exists(prompt_path):
            # Use content_manager.summarize to create a short executive summary
            for h in hits[:max_hits]:
                url = h.get("url")
                try:
                    summary = content_manager.summarize(url, prompt_path)
                except Exception as e:
                    logger.debug("Summarization failed for %s: %s", url, e)
                    summary = h.get("summary") or ""
                new_h = {**h}
                new_h["summary"] = summary
                compacted_hits.append(new_h)
        else:
            # No LLM available: fallback to score-based truncation
            try:
                sorted_hits = sorted(hits, key=lambda x: float(x.get("score", 0.0)), reverse=True)
            except Exception:
                sorted_hits = hits
            compacted_hits = sorted_hits[:max_hits]

        omitted = max(0, len(hits) - len(compacted_hits))
        compacted["hits"] = compacted_hits
        if omitted:
            compacted["omitted_count"] = omitted
            logger.info(
                "Compacted hits from %d to %d (omitted=%d)",
                len(hits),
                len(compacted_hits),
                omitted,
            )
        else:
            logger.info("Compaction produced %d hits", len(compacted_hits))

        return compacted

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
