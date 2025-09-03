from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
import time
import math

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
        # Store shared for helper access
        self.shared = shared

        compaction_attempts = shared.get("compaction_attempts", 0)
        max_compaction_attempts = int(self.params.get("max_compaction_attempts", 3))

        # Safety: bail out if we've reached the maximum number of compaction attempts
        if compaction_attempts >= max_compaction_attempts:
            logger.info(
                "Maximum compaction attempts (%d) reached. Cannot reduce context further.",
                max_compaction_attempts,
            )
            return None

        memory = shared.get("memory", {})
        hits = memory.get("hits", []) if isinstance(memory, dict) else []

        # If we already have very few conversations, prefer to proceed anyway
        if len(hits) <= 3:
            logger.info(
                "Cannot compact further — only %d conversations remain."
                " Proceeding with minimal context.",
                len(hits),
            )
            return "proceed_anyway"

        logger.info(
            "Attempt %d/%d: Compacting research context to fit model limits",
            compaction_attempts + 1,
            max_compaction_attempts,
        )
        logger.info("Starting with %d conversations", len(hits))

        # Sort conversations by priority (in place)
        self.sort_conversations_by_priority(hits)

        # Determine strategy and removal count based on attempt number
        if compaction_attempts == 0:
            removal_count = math.ceil(len(hits) * 0.3)
            strategy = "Remove bottom 30% by priority"
        elif compaction_attempts == 1:
            removal_count = math.ceil(len(hits) * 0.5)
            strategy = "Remove bottom 50% by priority and strip conversation details"
        else:
            # Final attempt: keep only top 25% with minimal data
            keep = max(1, math.ceil(len(hits) * 0.25))
            removal_count = max(0, len(hits) - keep)
            strategy = "Keep only top 25% with minimal data"

        logger.info("Strategy: %s", strategy)
        logger.info(
            "Will remove %d conversations, keeping %d",
            removal_count,
            len(hits) - removal_count,
        )

        # Remove lower-priority conversations
        if removal_count > 0:
            removed_conversations = hits[-removal_count:]
            del hits[-removal_count:]
        else:
            removed_conversations = []

        # For more aggressive attempts, strip conversation details to save space
        if compaction_attempts >= 1:
            logger.info("Stripping conversation details to reduce context size...")
            for idx, hit in enumerate(hits):
                convo = hit.get("conversation")
                if not isinstance(convo, dict):
                    continue
                essential = {}
                # Preserve common, essential fields when present
                if convo.get("title"):
                    essential["title"] = convo.get("title")
                if convo.get("state"):
                    essential["state"] = convo.get("state")
                if convo.get("url"):
                    essential["url"] = convo.get("url")
                if convo.get("created_at"):
                    essential["created_at"] = convo.get("created_at")
                if convo.get("updated_at"):
                    essential["updated_at"] = convo.get("updated_at")
                # PR-specific
                if convo.get("merged") is not None:
                    essential["merged"] = convo.get("merged")

                # Preserve structural counts where available
                try:
                    essential["comments_count"] = len(convo.get("comments", []))
                except Exception:
                    essential["comments_count"] = 0
                try:
                    essential["reviews_count"] = len(convo.get("reviews", []))
                except Exception:
                    essential["reviews_count"] = 0
                try:
                    essential["review_comments_count"] = len(convo.get("review_comments", []))
                except Exception:
                    essential["review_comments_count"] = 0

                hit["conversation"] = essential

        # Update the memory structure returned for compaction
        compacted_memory = dict(memory)
        compacted_memory["hits"] = hits

        return {
            "strategy": strategy,
            "removed_count": len(removed_conversations),
            "remaining_count": len(hits),
            "compaction_attempt": compaction_attempts + 1,
        }

    def exec(self, context):
        """Perform compaction of the provided context.

        Args:
            context : The memory/context to compact.

        Returns:
            The compacted memory/context.

        """
        logger.info("Compaction exec: passing through compaction info for post-processing")
        # If prep returned a sentinel value, preserve it
        if context is None:
            return None
        if context == "proceed_anyway":
            return "proceed_anyway"
        # Otherwise just return the compaction_info unchanged for post()
        logger.info("Applied compaction strategy: %s", context.get("strategy"))
        logger.info("Removed %d conversations", context.get("removed_count"))
        logger.info("%d conversations remaining", context.get("remaining_count"))
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
        # Handle cases where compaction wasn't performed or was bypassed
        if prep_res is None or exec_res == "proceed_anyway":
            return "proceed_anyway"

        # Apply the compaction to shared memory: note prep_res contained the
        # memory snapshot and exec_res contains compaction metadata; we
        # stored hits in prep step mutation. Ensure the counter is
        # incremented.
        shared["compaction_attempts"] = shared.get("compaction_attempts", 0) + 1
        logger.info(
            "\u2713 Context compaction attempt %d completed",
            shared["compaction_attempts"],
        )

        # Rate-limit/backoff delay before retrying to reduce immediate
        # rejections
        sleep_duration = int(self.params.get("compaction_sleep_seconds", 60))
        logger.info(
            "Waiting %d seconds after compaction before retrying...",
            sleep_duration,
        )
        try:
            time.sleep(sleep_duration)
        except Exception:
            pass

        return "retry"

    def sort_conversations_by_priority(self, hits: list) -> list:
        """Sort conversations in-place by a composite priority score.

        Higher-priority conversations will appear first in the list.
        """
        if not isinstance(hits, list):
            return hits

        total = len(hits)
        scored = []
        for idx, h in enumerate(hits):
            composite = 0.0
            if str(h.get("summary", "")).strip():
                composite += 10.0
            try:
                composite += float(h.get("score", 0.0))
            except Exception:
                pass
            # Bonus for earlier discovery (lower index means earlier)
            composite += (total - idx) * 0.1
            scored.append((composite, h))

        # Sort by composite descending and replace hits in-place
        scored.sort(key=lambda x: x[0], reverse=True)
        hits[:] = [h for _, h in scored]
        return hits
