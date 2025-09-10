from typing import Tuple

from ...pocketflow import Node
from ...clients.llm import llm_client
from ...utils.utils import get_logger

logger = get_logger(__name__)


class SupervisorNode(Node):
    def prep(self, shared):
        """Get the current answer for evaluation."""
        context = shared.get("context", "No previous search")
        question = shared["question"]
        answer = shared["answer"]
        return question, context, answer

    def exec(self, input_tp: Tuple[str, str, str]):
        """Check if the answer is valid or nonsensical."""
        logger.info("🔍 Supervisor checking answer quality...")

        question, context, answer = input_tp

        # Create a prompt for the LLM to determine whether the question was answered correctly
        prompt = f"""
            ### CONTEXT
            Based on the following information:
             - Question: {question}
             - Research: {context}
             - Answer: {answer}

            Determine whether the answer provided was accurate or not.

            ## YOUR RESPONSE:
            Return your response in this format:

            ```yaml
            valid: true OR false
            reason: <explanation of the decision>
            ```

            """
        # Call the LLM to generate an answer
        result_dc, response_dc = llm_client.generate(prompt)

        return result_dc

        if result_dc.get("valid"):
            return {"valid": True, "reason": "Answer appears to be legitimate."}
        else:
            return {"valid": False, "reason": "Answer appears to be nonsensical or unhelpful."}

    def post(self, shared, prep_res, exec_res):
        """Decide whether to accept the answer or restart the process."""
        if exec_res["valid"]:
            logger.info(f"✅ Supervisor approved answer: {exec_res['reason']}")
        else:
            logger.info(f"❌ Supervisor rejected answer: {exec_res['reason']}")
            # Clean up the bad answer
            shared["answer"] = None
            # Add a note about the rejected answer
            context = shared.get("context", "")
            shared["context"] = (
                context + "\n\nNOTE: Previous answer attempt was rejected by supervisor."
            )
            return "retry"
