from ..agent.pocketflow import Node
from ..agent.log import info
from .retriever_node import RetrieverNode


class ParallelRetrieverNode(RetrieverNode):
    def prep(self, shared):
        info("=== PARALLEL RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        info("Executing parallel search operations...")
        results = [
            {
                "url": "https://github.com/example/conversation/3",
                "summary": "Parallel retrieved summary",
                "score": 0.92,
                "search_mode": "keyword",
                "conversation": {},
            }
        ]
        return results
