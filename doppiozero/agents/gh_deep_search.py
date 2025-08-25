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


class GitHubAgent:
    """Encapsulates the GitHub Conversations Research Agent.

    This mirrors the Ruby `GitHubDeepResearchAgent` by holding configuration
    and exposing methods to run the node-based Flow or a pragmatic
    `run_deep_search` orchestration.
    """

    def __init__(self, request: str, options: dict):
        self.request = request
        self.options = options or {}
        self.logger = logger

        # Shared runtime state passed through the flow
        self.shared = {
            "request": request,
            "collection": self.options.get("collection"),
            "top_k": self.options.get("limit", 5),
            "max_depth": self.options.get("max_depth", 2),
            "editor_file": self.options.get("editor_file"),
            "clarifying_qa": self.options.get("clarifying_qa"),
            "verbose": self.options.get("verbose", False),
            "search_modes": self.options.get("search_modes", ["semantic", "keyword"]),
            "cache_path": self.options.get("cache_path"),
            # Ensure reasonable defaults for model names so nodes can assume
            # keys exist. Users may override via options['models'].
            "models": {
                **{
                    "fast": self.options.get("fast_model")
                    or self.options.get("models", {}).get("fast")
                    or "default",
                    "reasoning": self.options.get("reasoning_model")
                    or self.options.get("models", {}).get("reasoning")
                    or "default",
                    "embed": self.options.get("embed_model")
                    or self.options.get("models", {}).get("embed")
                    or "default",
                },
                **(self.options.get("models") or {}),
            },
            "script_dir": self.options.get("script_dir", "bin"),
            "parallel": self.options.get("parallel", False),
            "done": False,
        }

        # Build the Flow graph using node classes
        self._build_flow()

    def _build_flow(self):
        # Node classes were imported at module top-level
        initial_node = InitialResearchNode()
        clarify_node = AskClarifyingNode()
        planner_node = PlannerNode()
        retriever_node = ParallelRetrieverNode() if self.shared["parallel"] else RetrieverNode()
        compaction_node = ContextCompactionNode()
        claim_verifier_node = (
            ParallelClaimVerifierNode() if self.shared["parallel"] else ClaimVerifierNode()
        )
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

        self.flow = Flow(initial_node)

    def run(self):
        self.logger.info(
            f"=== GITHUB CONVERSATIONS RESEARCH AGENT{' (parallel mode)' if self.shared['parallel'] else ''} ==="
        )
        self.logger.info(f"Request: {self.request}")
        self.logger.info(f"Collection: {self.options.get('collection')}")
        self.logger.info(f"Max results per search: {self.shared['top_k']}")
        self.logger.info(f"Max deep research iterations: {self.shared['max_depth']}")
        self.logger.info(f"Fast model: {self.shared['models'].get('fast', 'default')}")
        self.logger.info(f"Reasoning model: {self.shared['models'].get('reasoning', 'default')}")
        return self.flow.run(self.shared)


def start(request: str, options: dict):
    """Compatibility wrapper: instantiate GitHubAgent and run the Flow."""
    agent = GitHubAgent(request, options or {})
    return agent.run()


def run_deep_search(request: str, options: dict):
    """A pragmatic deep-search orchestration that uses existing helper modules.

    This function provides a concrete implementation while the Node classes are
    progressively improved. It performs iterative search -> fetch -> summarize ->
    (optional) upsert passes.
    """
    from ..search_github_conversations import search_github_conversations
    from ..fetch_github_conversation import fetch_github_conversation
    from ..summarize_github_conversation import summarize_github_conversation
    from ..vector_upsert import vector_upsert

    collection = options.get("collection")
    limit = options.get("limit", 5)
    max_depth = options.get("max_depth", 2)
    cache_path = options.get("cache_path")
    prompt_path = options.get("executive_summary_prompt_path", "")
    models = options.get("models", {})

    all_hits = []

    for depth in range(max_depth):
        q = f"{request} (pass {depth+1})"
        logger.info(f"Searching (pass {depth+1}): {q}")
        results = search_github_conversations(q, max_results=limit)
        for r in results:
            url = r.get("url")
            if not url:
                continue
            logger.info(f"Fetching conversation: {url}")
            convo = fetch_github_conversation(url, cache_path=cache_path)
            summary = ""
            try:
                if prompt_path:
                    summary = summarize_github_conversation(url, prompt_path, cache_path=cache_path)
                else:
                    summary = f"Summary for {url} (no prompt provided)"
            except Exception as e:
                logger.warning(f"Summary failed for {url}: {e}")
            hit = {
                "url": url,
                "summary": summary,
                "score": r.get("score", 0.9),
                "conversation": convo,
            }
            all_hits.append(hit)
            # Optionally upsert to vector DB
            try:
                if collection:
                    vector_upsert(
                        summary or url, collection, {"url": url}, model=models.get("embed")
                    )
            except Exception as e:
                logger.warning(f"Vector upsert failed for {url}: {e}")

    report = {
        "request": request,
        "results": all_hits,
        "summary": f"Collected {len(all_hits)} conversations",
    }
    return report
