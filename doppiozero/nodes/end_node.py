from ..agent.pocketflow import Node
from ..agent.log import info


class EndNode(Node):
    def exec(self, shared):
        info("End node: terminating workflow and returning results.")
        return None
