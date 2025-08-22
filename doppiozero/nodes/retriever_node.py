from ..agent.pocketflow import Node
from ..agent.log import info


class RetrieverNode(Node):
    def prep(self, shared):
        info("=== RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        info("Executing search operations and retrieving data...")
        results = [
            {
                "url": "https://github.com/example/conversation/2",
                "summary": "Retrieved summary",
                "score": 0.90,
                "search_mode": "semantic",
                "conversation": {},
            }
        ]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["memory"]["hits"].extend(exec_res)
        shared["memory"]["search_queries"].append(", ".join([plan["query"] for plan in prep_res]))
        info(f"Added {len(exec_res)} new conversations to memory.")
        shared["current_depth"] = shared.get("current_depth", 0) + 1
        if shared["current_depth"] < shared["max_depth"]:
            return "continue"
        else:
            return "final"
