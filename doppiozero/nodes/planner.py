from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class PlannerNode(Node):
    def prep(self, shared):
        logger.info("=== PLANNING PHASE ===")
        return {
            "semantic": {"query": shared["request"] + " implementation details"},
            "keyword": {"query": "repo:example is:issue"},
        }

    def exec(self, plan):
        logger.info("Transforming queries into search plans...")
        return [
            {"tool": "semantic", "query": plan["semantic"]["query"]},
            {"tool": "keyword", "query": plan["keyword"]["query"]},
        ]

    def post(self, shared, prep_res, exec_res):
        shared["next_search_plans"] = exec_res
        logger.info(f"✓ Planning complete, generated {len(exec_res)} search plans")
        return None
