from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class EndNode(Node):
    def exec(self, shared):
        logger.info("End node: terminating workflow and returning results.")
        return None
