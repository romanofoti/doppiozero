from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class EndNode(Node):
    def prep(self, shared):
        # Keep a reference to shared so exec can return results. Base Flow
        # passes prep(shared) -> exec(prep_res) where prep_res is often None,
        # so we must capture shared explicitly here.
        self.shared = shared

    def exec(self, _prep_res):
        logger.info("End node: terminating workflow and returning results.")
        # Return any structured final report placed into shared by earlier
        # nodes (FinalReportNode). Fall back to the full shared dict.
        return getattr(self, "shared", {}).get("final_report", getattr(self, "shared", {}))

    def post(self, shared, prep_res, exec_res):
        # Return the exec result so Flow._orch returns it as the final value.
        return exec_res
