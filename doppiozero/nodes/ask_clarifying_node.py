from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class AskClarifyingNode(Node):
    def prep(self, shared):
        logger.info("=== CLARIFYING QUESTIONS PHASE ===")
        return ["What is the main goal?", "Are there specific repos to focus on?"]

    def exec(self, questions):
        logger.info("Presenting clarifying questions to user...")
        clarifications = "No further clarifications."
        return clarifications

    def post(self, shared, prep_res, exec_res):
        shared["clarifications"] = exec_res
        logger.info("Clarifications stored.")
        return None
