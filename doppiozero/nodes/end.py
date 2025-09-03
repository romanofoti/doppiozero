from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class End(Node):
    """Terminal node.

    Notes
    -----
    The End node is the terminal node for flows and simply returns None so that the workflow stops.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use injected logger when provided, otherwise fall back to module logger
        self.logger = get_logger(__name__)

    def exec(self, _prep_res):
        """Return the final report or the full shared state.

        Returns:
            The structured final report if present under ``final_report``. Otherwise
            returns the full shared state.

        """
        self.logger.info("End node: terminating workflow and returning results.")
        return None
