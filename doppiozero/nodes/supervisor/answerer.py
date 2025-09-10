import random

from ...clients.llm import llm_client
from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class UnreliableAnswerNode(Node):
    def prep(self, shared):
        """Get the question and context for answering."""
        return shared["question"], shared.get("context", "")

    def exec(self, inputs):
        """Call the LLM to generate a final answer with 50% chance of returning a dummy answer."""
        question, context = inputs

        # 50% chance to return a dummy answer
        if random.random() < 0.5:
            logger.info("🤪 Generating unreliable dummy answer...")
            return "Sorry, I'm on a coffee break right now. All information I provide is completely made up anyway. The answer to your question is 42, or maybe purple unicorns. Who knows? Certainly not me!"

        logger.info("✍️ Crafting final answer...")

        # Create a prompt for the LLM to answer the question
        prompt = f"""
            ### CONTEXT
            Based on the following information, answer the question.
            Question: {question}
            Research: {context}

            ## YOUR ANSWER:
            Provide a comprehensive answer using the research results.
            """
        # Call the LLM to generate an answer
        result_dc, response_dc = llm_client.generate(prompt)

        return result_dc

    def post(self, shared, prep_res, exec_res):
        """Save the final answer and complete the flow."""
        # Save the answer in the shared store
        shared["answer"] = exec_res

        logger.info("✅ Answer generated successfully!")
