import json
import logging
from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class InitialResearchNode(Node):
    def prep(self, shared):
        logger.info("=== INITIAL RESEARCH PHASE ===")
        logger.info(f"Starting initial semantic search for: {shared['request']}")
        return {"query": shared["request"]}

    def exec(self, plan):
        logger.info("Executing initial semantic search and enriching results...")
        result_ls = [
            {
                "url": "https://github.com/example/conversation/1",
                "summary": "Example summary",
                "score": 0.95,
                "conversation": {},
            }
        ]
        return result_ls

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = {"hits": exec_res, "notes": [], "search_queries": [shared["request"]]}
        logger.info(f"✓ Initial research complete: {len(exec_res)} conversations collected")
        return None
