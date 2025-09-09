from typing import Any, Dict

from ..pocketflow.pocketflow import Flow
from ..nodes.supervisor import ActionDecider, Answerer, Supervisor, WebSearcher
from ..utils.utils import get_logger

logger = get_logger(__name__)


class SupervisorAgent:

    def __init__(self, param_dc: Dict[str, Any]):
        """Initialize the agent with a request and options.

        Args:
            param_dc: A mapping of optional parameters (collection, models, etc.).

        The initializer creates `self.shared` runtime state used by the
        Flow nodes and then builds the flow graph.

        """
        self.param_dc = param_dc or {}
        self.logger = logger

    def create_unsupervised_flow(self):
        """
        Create the inner research agent flow without supervision.

        This flow handles the research cycle:
        1. ActionDecider node decides whether to search or answer
        2. If search, go to WebSearcher node and return to decide
        3. If answer, go to Answerer node

        Returns:
            Flow: A research agent flow
        """
        # Create instances of each node
        decide = ActionDecider()
        search = WebSearcher()
        answer = Answerer()

        # Connect the nodes
        # If DecideAction returns "search", go to SearchWeb
        decide - "search" >> search

        # If DecideAction returns "answer", go to UnreliableAnswerNode
        decide - "answer" >> answer

        # After SearchWeb completes and returns "decide", go back to DecideAction
        search - "decide" >> decide

        # Create and return the inner flow, starting with the ActionDecider node
        return Flow(start=decide)

    def create_supervised_flow():
        """
        Create a supervised agent flow by treating the entire agent flow as a node
        and placing the supervisor outside of it.

        The flow works like this:
        1. Inner agent flow does research and generates an answer
        2. SupervisorNode checks if the answer is valid
        3. If answer is valid, flow completes
        4. If answer is invalid, restart the inner agent flow

        Returns:
            Flow: A complete research agent flow with supervision
        """
        # Create the inner flow
        agent_flow = self.create_unsupervised_flow()

        # Create the supervisor node
        supervisor = Supervisor()

        # Connect the components
        # After agent_flow completes, go to supervisor
        agent_flow >> supervisor

        # If supervisor rejects the answer, go back to agent_flow
        supervisor - "retry" >> agent_flow

        # Create and return the outer flow, starting with the agent_flow
        return Flow(start=agent_flow)
