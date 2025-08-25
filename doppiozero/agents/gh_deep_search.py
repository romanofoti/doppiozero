"""
GitHubDeepResearchAgent - Multi-Stage Research Pipeline for GitHub Conversations (Python)
"""

from ..pocketflow.pocketflow import Node, Flow
from ..utils.utils import get_logger

# Import nodes at module top-level. If circular imports appear, fix the
# referencing module rather than delaying imports here.
from ..nodes import (
    InitialResearchNode,
    AskClarifyingNode,
    PlannerNode,
    RetrieverNode,
    ParallelRetrieverNode,
    ContextCompactionNode,
    ClaimVerifierNode,
    ParallelClaimVerifierNode,
    FinalReportNode,
    EndNode,
)

logger = get_logger(__name__)


def start(request: str, options: dict):
    """Start the GitHub Conversations Research Agent workflow.

    Args:
        request: natural language research request
        options: dict of options (collection, limit, max_depth, etc.)
    """
    # Delay import of nodes to avoid circular imports at module import time
    from ..nodes import (
        InitialResearchNode,
        AskClarifyingNode,
        PlannerNode,
        RetrieverNode,
        ParallelRetrieverNode,
        ContextCompactionNode,
        ClaimVerifierNode,
        ParallelClaimVerifierNode,
        FinalReportNode,
        EndNode,
    )

    shared = {
        "request": request,
        "collection": options.get("collection"),
        "top_k": options.get("limit", 5),
        "max_depth": options.get("max_depth", 2),
        "editor_file": options.get("editor_file"),
        "clarifying_qa": options.get("clarifying_qa"),
        "verbose": options.get("verbose", False),
        "search_modes": options.get("search_modes", ["semantic", "keyword"]),
        "cache_path": options.get("cache_path"),
        "models": options.get("models", {}),
        "script_dir": options.get("script_dir", "bin"),
        "parallel": options.get("parallel", False),
        "done": False,
    }

    # Build nodes
    initial_node = InitialResearchNode()
    clarify_node = AskClarifyingNode()
    planner_node = PlannerNode()
    retriever_node = ParallelRetrieverNode() if shared["parallel"] else RetrieverNode()
    compaction_node = ContextCompactionNode()
    claim_verifier_node = ParallelClaimVerifierNode() if shared["parallel"] else ClaimVerifierNode()
    final_node = FinalReportNode()
    end_node = EndNode()

    # Link nodes
    initial_node.next(clarify_node)
    clarify_node.next(planner_node)
    planner_node.next(retriever_node)
    retriever_node.next(planner_node, action="continue")
    retriever_node.next(final_node, action="final")
    final_node.next(claim_verifier_node, action="verify")
    final_node.next(end_node, action="complete")
    claim_verifier_node.next(final_node, action="ok")
    claim_verifier_node.next(planner_node, action="fix")
    final_node.next(compaction_node, action="compact")
    compaction_node.next(final_node, action="retry")
    compaction_node.next(final_node, action="proceed_anyway")
    final_node.next(end_node)

    flow = Flow(initial_node)

    logger.info(
        f"=== GITHUB CONVERSATIONS RESEARCH AGENT{' (parallel mode)' if shared['parallel'] else ''} ==="
    )
    logger.info(f"Request: {request}")
    logger.info(f"Collection: {options.get('collection')}")
    logger.info(f"Max results per search: {shared['top_k']}")
    logger.info(f"Max deep research iterations: {shared['max_depth']}")
    logger.info(f"Fast model: {shared['models'].get('fast', 'default')}")
    logger.info(f"Reasoning model: {shared['models'].get('reasoning', 'default')}")

    return flow.run(shared)
