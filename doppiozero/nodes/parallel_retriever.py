from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from .retriever import RetrieverNode


logger = get_logger(__name__)


class ParallelRetrieverNode(RetrieverNode):
    def prep(self, shared):
        logger.info("=== PARALLEL RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        logger.info("Executing parallel search operations...")
        result_ls = [
            {
                "url": "https://github.com/example/conversation/3",
                "summary": "Parallel retrieved summary",
                "score": 0.92,
                "search_mode": "keyword",
                "conversation": {},
            }
        ]
        return result_ls
