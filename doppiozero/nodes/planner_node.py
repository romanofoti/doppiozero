from ..agent.pocketflow import Node
from ..agent.log import info


class PlannerNode(Node):
    def prep(self, shared):
        info("=== PLANNING PHASE ===")
        return {
            "semantic": {"query": shared["request"] + " implementation details"},
            "keyword": {"query": "repo:example is:issue"},
        }

    def exec(self, plan):
        info("Transforming queries into search plans...")
        return [
            {"tool": "semantic", "query": plan["semantic"]["query"]},
            {"tool": "keyword", "query": plan["keyword"]["query"]},
        ]

    def post(self, shared, prep_res, exec_res):
        shared["next_search_plans"] = exec_res
        info(f"✓ Planning complete, generated {len(exec_res)} search plans")
        return None
