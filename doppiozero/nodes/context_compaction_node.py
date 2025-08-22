from ..agent.pocketflow import Node
from ..agent.log import info


class ContextCompactionNode(Node):
    def prep(self, shared):
        info("=== CONTEXT COMPACTION PHASE ===")
        return shared.get("memory", {})

    def exec(self, context):
        info("Compacting context for LLM constraints...")
        return context

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = exec_res
        shared["compaction_attempts"] = shared.get("compaction_attempts", 0) + 1
        info("Context compaction complete.")
        return "retry"
