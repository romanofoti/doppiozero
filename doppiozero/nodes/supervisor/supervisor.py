import json
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
        answer = shared.get("answer", "No previous answer")
        return question, context, answer, shared.get("verbose", False)

    def exec(self, input_tp: Tuple[str, str, str, bool]):
        """Check if the answer is valid or nonsensical."""
        logger.info("🔍 Supervisor checking answer quality...")

        question, context, answer, verbose = input_tp

        # Create a prompt for the LLM to determine whether the question was answered correctly
        prompt = f"""
            ### CONTEXT
            Based on the following information:
             - Question: {question}
             - Research: {context}
             - Answer: {answer}

            Determine whether the answer provided is acceptable or not. It does not need to be
            perfect or 100% accurate. Being a reasonable response is sufficient to consider it as
            valid.

            ## YOUR RESPONSE:
            Return your response in this format, making sure to adhere to it:

            ```yaml
            valid: true OR false
            reason: <explanation of the decision>
            ```

            """
        # Call the LLM to generate an answer
        result_dc, response_dc = llm_client.generate(prompt)
        logger.info("LLM call completed.")
        if verbose:
            logger.info(f"Generated the following result: {json.dumps(result_dc, indent=2)}")

        if result_dc.get("valid"):
            return {"valid": True, "reason": result_dc.get("reason", "No reason provided.")}
        else:
            return {"valid": False, "reason": result_dc.get("reason", "No reason provided.")}

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
                context
                + "\n\nNOTE: Previous answer attempt was rejected by supervisor with the"
                + f"following reason: {exec_res['reason']}"
            )
            return "retry"
