import json

from ...clients.llm import llm_client
from ...pocketflow.pocketflow import Node
from ...utils.utils import get_logger

logger = get_logger(__name__)


class AnswererNode(Node):
    def prep(self, shared):
        """Get the question and context for answering."""
        return shared["question"], shared.get("context", ""), shared.get("verbose", False)

    def exec(self, inputs):
        """Call the LLM to generate a final answer with 50% chance of returning a dummy answer."""
        question, context, verbose = inputs

        # Create a prompt for the LLM to answer the question
        prompt = f"""
            ### CONTEXT
            Based on the following information, answer the question.
            Question: {question}
            Research: {context}

            ## YOUR ANSWER:
            Provide a comprehensive answer using the research results.
            Return your response in this format:

            ```yaml
            answer: <your comprehensive answer>
            ```
        """
        # Call the LLM to generate an answer
        result_dc, response_dc = llm_client.generate(prompt)
        logger.info("LLM call completed.")
        if verbose:
            logger.info(f"Generated the following result: {json.dumps(result_dc, indent=2)}")
        return result_dc.get("answer", "No acceptable answer found.")

    def post(self, shared, prep_res, exec_res):
        """Save the final answer and complete the flow."""
        # Save the answer in the shared store
        shared["answer"] = exec_res

        logger.info("✅ Answer generated successfully!")
