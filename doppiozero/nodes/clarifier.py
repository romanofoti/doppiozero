from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

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
        return ["What is the main goal?", "Are there specific repos to focus on?"]

    def exec(self, questions):
        """Simulate presenting questions to the user and collect clarifications.

        Args:
            questions : The questions returned by :meth:`prep`.

        Returns:
            A simple clarification string (in production this would be user-provided answers).

        """
        logger.info("Presenting clarifying questions to user...")
        clarifications = "No further clarifications."
        return clarifications

    def post(self, shared, prep_res, exec_res):
        """Store clarifications into the shared flow state.

        Args:
            shared : Shared flow state to update.
            prep_res : The questions that were asked.
            exec_res : The clarifications collected from the user.

        Returns:
            None

        """
        shared["clarifications"] = exec_res
        logger.info("Clarifications stored.")
        return None
