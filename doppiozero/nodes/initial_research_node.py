import json
import logging
from ..agent.pocketflow import Node
from ..agent.log import info


class InitialResearchNode(Node):
    def prep(self, shared):
        info("=== INITIAL RESEARCH PHASE ===")
        info(f"Starting initial semantic search for: {shared['request']}")
        return {"query": shared["request"]}

    def exec(self, plan):
        info("Executing initial semantic search and enriching results...")
        results = [
            {
                "url": "https://github.com/example/conversation/1",
                "summary": "Example summary",
                "score": 0.95,
                "conversation": {},
            }
        ]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = {"hits": exec_res, "notes": [], "search_queries": [shared["request"]]}
        info(f"✓ Initial research complete: {len(exec_res)} conversations collected")
        return None
