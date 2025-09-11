from typing import Any, Dict

from ..pocketflow.pocketflow import Flow, Node
from ..nodes.supervisor import DeciderNode, AnswererNode, SearcherNode, SupervisorNode
from ..utils.utils import get_logger

logger = get_logger(__name__)


class SupervisorAgent(Flow):
    """Agent that performs iterative research with an optional supervision loop.

    The design separates two layers:
    1. Unsupervised research cycle (decide -> search/answer) that accumulates context.
    2. Supervisory evaluation (optional) that can reject an answer and trigger a retry.

    Parameters
    ----------
    param_dc : Dict[str, Any], optional
        Configuration parameters (e.g. model selectors, collection names, limits). Stored
        for prospective extensibility; not all keys are currently consumed.

    Attributes
    ----------
    start_node : Node
        Entry point of the (supervised) flow once assembled.
    param_dc : Dict[str, Any]
        User-supplied configuration mapping.
    logger : logging.Logger
        Logger instance for structured output.

    """

    def __init__(self, param_dc: Dict[str, Any] = None):
        super().__init__()
        self.param_dc = param_dc or {}
        self.logger = logger

    def create_unsupervised_flow(self, return_flow: bool = False) -> Flow:
        """Build the core research loop without supervision.

        The loop topology:
            Decider --(search)--> Searcher --(decide)--> Decider
            Decider --(answer)--> Answerer (terminal branch)

        Args:
            return_flow : if True, wrap and return the start node in a ``Flow`` (useful for nesting
                          inside a supervising wrapper). If False, return the raw start ``Node``.

        Returns:
        Node or Flow
            DeciderNode when ``return_flow`` is False, otherwise a Flow(start=DeciderNode).

        """
        decide = DeciderNode()
        search = SearcherNode()
        answer = AnswererNode()

        decide - "search" >> search
        decide - "answer" >> answer
        search - "decide" >> decide

        self.start_node = decide
        if return_flow:
            return Flow(start=decide)

    def create_supervised_flow(self) -> None:
        """Compose a supervised variant of the research loop.

        Layout:
            [InnerFlow] -> Supervisor --(retry)--> [InnerFlow]

        The inner flow (built via ``create_unsupervised_flow(return_flow=True)``) is treated
        as a single node. The supervisor evaluates the produced answer and either ends the
        run (no action) or emits ``"retry"`` to re-enter the inner loop.

        """

        agent_flow = self.create_unsupervised_flow(return_flow=True)  # Flow instance
        supervisor = SupervisorNode()

        class TerminalNode(Node):
            pass

        terminal = TerminalNode()

        # Wire the inner research flow to the supervisor, then either retry or end.
        agent_flow >> supervisor  # default successor from inner flow
        supervisor >> terminal  # default (approval) path
        supervisor - "retry" >> agent_flow  # rejection loops back
        self.start_node = agent_flow
