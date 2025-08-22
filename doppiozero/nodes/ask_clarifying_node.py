from ..agent.pocketflow import Node
from ..agent.log import info


class AskClarifyingNode(Node):
    def prep(self, shared):
        info("=== CLARIFYING QUESTIONS PHASE ===")
        return ["What is the main goal?", "Are there specific repos to focus on?"]

    def exec(self, questions):
        info("Presenting clarifying questions to user...")
        clarifications = "No further clarifications."
        return clarifications

    def post(self, shared, prep_res, exec_res):
        shared["clarifications"] = exec_res
        info("Clarifications stored.")
        return None
