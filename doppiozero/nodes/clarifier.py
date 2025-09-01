from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..clients.llm import llm_client

logger = get_logger(__name__)


class ClarifierNode(Node):
    """Node that generates and processes clarifying questions.

    Parameters
    ----------
    None

    Attributes
    ----------
    logger : logging.Logger
        Module-level logger obtained via :func:`doppiozero.utils.utils.get_logger`.
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.

    Notes
    -----
    This node generates clarifying questions and stores user-provided
    clarifications in the shared state under the ``clarifications`` key.

    """

    def prep(self, shared):
        """Return a list of clarifying questions to present to the user.

        Args:
            shared : Shared flow state (unused by this preparer but provided for API consistency).

        Returns:
            A list of question strings to ask the user.

        """
        logger.info("=== CLARIFYING QUESTIONS PHASE ===")
        # If clarifications already exist, don't ask again.
        if shared.get("clarifications"):
            logger.debug("Clarifications already present; skipping question generation.")
            return []
        # Default question set when LLM is not available or returns nothing
        default_qs = ["What is the main goal?", "Are there specific repos to focus on?"]
        # If an LLM is available, ask it to generate 3 focused clarifying questions
        if llm_client:
            try:
                prompt = (
                    "You are a helpful assistant that generates concise clarifying "
                    "questions to better understand a user's research request. "
                    "Return a JSON array of short questions.\n\nRequest:\n"
                    + str(shared.get("request", ""))
                )
                raw = llm_client.generate(prompt)
                # Try to parse JSON array; fall back to newline splitting
                try:
                    import json

                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and parsed:
                        return [str(q).strip() for q in parsed]
                except Exception:
                    lines = [line.strip() for line in raw.splitlines() if line.strip()]
                    if lines:
                        return lines[:5]
            except Exception as e:
                logger.debug("LLM clarifier failed: %s", e)
                return default_qs
        return default_qs

    def exec(self, questions):
        """Simulate presenting questions to the user and collect clarifications.

        Args:
            questions : The questions returned by :meth:`prep`.

        Returns:
            A simple clarification string (in production this would be user-provided answers).

        """
        logger.info("Presenting clarifying questions to user...")
        # In automated runs we may auto-answer using the LLM (or default)
        if not questions:
            return []
        answers = []
        for q in questions:
            try:
                if llm_client:
                    ans = llm_client.generate(f"Q: {q}\nA:")
                else:
                    ans = "No clarification provided."
            except Exception:
                ans = "No clarification provided."
            answers.append({"question": q, "answer": ans})
        # Return structured clarifications
        return answers

    def post(self, shared, prep_res, exec_res):
        """Store clarifications into the shared flow state.

        Args:
            shared : Shared flow state to update.
            prep_res : The questions that were asked.
            exec_res : The clarifications collected from the user.

        Returns:
            None

        """
        # Store structured clarifications; normalize simple strings to a list.
        if isinstance(exec_res, str):
            shared["clarifications"] = [{"question": None, "answer": exec_res}]
        else:
            shared["clarifications"] = exec_res
        logger.info("Clarifications stored.")
        return None
