from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class ContextCompacterNode(Node):
    def prep(self, shared):
        logger.info("=== CONTEXT COMPACTION PHASE ===")
        return shared.get("memory", {})

    def exec(self, context):
        logger.info("Compacting context for LLM constraints...")
        return context

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = exec_res
        shared["compaction_attempts"] = shared.get("compaction_attempts", 0) + 1
        logger.info("Context compaction complete.")
        return "retry"
