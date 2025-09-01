from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class End(Node):
    """Terminal node that returns the flow results to the caller.

    Parameters
    ----------
    None

    Attributes
    ----------
    shared : dict
        A reference to the shared flow state captured during prep and returned
        by :meth:`exec`.

    Notes
    -----
    The End node is the terminal node for flows and simply returns the
    structured final report when present, or the whole shared state as a
    fallback.

    """

    def prep(self, shared):
        """Capture shared state for later retrieval in exec.

        Args:
            shared : The shared flow state to capture.

        """
        # Keep a reference to shared so exec can return results. Base Flow
        # passes prep(shared) -> exec(prep_res) where prep_res is often None,
        # so we must capture shared explicitly here.
        self.shared = shared

    def exec(self, _prep_res):
        """Return the final report or the full shared state.

        Returns:
            The structured final report if present under ``final_report``. Otherwise
            returns the full shared state.

        """
        logger.info("End node: terminating workflow and returning results.")
        # Return any structured final report placed into shared by earlier
        # nodes (FinalReportNode). Fall back to the full shared dict.
        return getattr(self, "shared", {}).get("final_report", getattr(self, "shared", {}))

    def post(self, shared, prep_res, exec_res):
        """Return the exec result so the Flow orchestration returns it.

        Args:
            shared : The shared flow state (unused here).
            prep_res : The result from prep (often None).
            exec_res : The result from exec to be returned by the flow.

        Returns:
            The exec result passed through.

        """
        # Return the exec result so Flow._orch returns it as the final value.
        return exec_res
