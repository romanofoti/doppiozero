"""
GitHubDeepResearchAgent - Multi-Stage Research Pipeline for GitHub Conversations (Python)
"""

from ..pocketflow.pocketflow import Flow
from ..utils.utils import get_logger

from ..contents import content_manager, content_fetcher
from ..nodes import (
    InitialResearchNode,
    ClarifierNode,
    PlannerNode,
    RetrieverNode,
    ParallelRetrieverNode,
    ContextCompacterNode,
    VerifierNode,
    ParallelClaimVerifierNode,
    FinalReportNode,
    End,
)


logger = get_logger(__name__)


class GitHubAgent:
    """Encapsulates the GitHub Conversations Research Agent.

    Parameters
    ----------
    request : str
        The user's natural-language research request.
    options : dict
        Optional configuration mapping (collection, models, cache paths, etc.).

    Attributes
    ----------
    request : str
        The original request passed to the agent.
    options : dict
        The resolved options mapping used to configure the agent.
    logger : logging.Logger
        Module-level logger exposed on the instance for tests and debugging.
    shared : dict
        Runtime shared state passed through the Flow nodes.
    flow : Flow
        The constructed node-based Flow used to execute the multi-stage research.

    Notes
    -----
    This agent builds a node graph using the PocketFlow primitives and
    orchestrates semantic searches, clarifications, compaction and final
    report generation.

    """

    def __init__(self, request: str, options: dict):
        """Initialize the agent with a request and options.

        Args:
            request: The user's natural-language research request.
            options: A mapping of optional parameters (collection, models, etc.).

        The initializer creates `self.shared` runtime state used by the
        Flow nodes and then builds the flow graph.
        """
        # Save inputs
        self.request = request
        self.options = options or {}

        # Use module-level logger, but expose it on the instance for tests
        self.logger = logger

        # Build models defaults (allow explicit model keys or top-level shortcuts)
        provided_models = self.options.get("models") or {}
        model_dc = {
            **{
                "fast": self.options.get("fast_model") or provided_models.get("fast") or "default",
                "reasoning": self.options.get("reasoning_model")
                or provided_models.get("reasoning")
                or "default",
                "embed": self.options.get("embed_model")
                or provided_models.get("embed")
                or "default",
            },
            **provided_models,
        }

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
            "models": model_dc,
            "script_dir": self.options.get("script_dir", "bin"),
            "parallel": self.options.get("parallel", False),
            "done": False,
        }

        # Build the Flow graph using node classes
        self._build_flow()

    def _build_flow(self):
        """Construct the node Flow graph used by this agent.

        Returns:
            None

        """
        # Node classes were imported at module top-level
        initial_node = InitialResearchNode()
        clarify_node = ClarifierNode()
        planner_node = PlannerNode()
        retriever_node = ParallelRetrieverNode() if self.shared["parallel"] else RetrieverNode()
        compaction_node = ContextCompacterNode()
        claim_verifier_node = (
            ParallelClaimVerifierNode() if self.shared["parallel"] else VerifierNode()
        )
        final_node = FinalReportNode()
        end_node = End()

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
        """Run the configured Flow and return the final result.

        Returns:
            The final flow result returned by the Flow orchestration.

        """
        # Avoid extremely long inline f-strings; build suffix separately
        suffix = " (parallel mode)" if self.shared["parallel"] else ""
        self.logger.info(f"=== GITHUB CONVERSATIONS RESEARCH AGENT{suffix} ===")
        self.logger.info(f"Request: {self.request}")
        self.logger.info(f"Collection: {self.options.get('collection')}")
        self.logger.info(f"Max results per search: {self.shared['top_k']}")
        self.logger.info(f"Max deep research iterations: {self.shared['max_depth']}")
        self.logger.info(f"Fast model: {self.shared['models'].get('fast', 'default')}")
        self.logger.info(f"Reasoning model: {self.shared['models'].get('reasoning', 'default')}")
        return self.flow.run(self.shared)


def start(request: str, options: dict):
    """Compatibility wrapper: instantiate GitHubAgent and run the Flow.

    Args:
        request : The user's research request.
        options : Optional configuration mapping.

    Returns:
        The final result of running the agent's Flow.

    """
    agent = GitHubAgent(request, options or {})
    return agent.run()


def run_deep_search(request: str, options: dict):
    """A pragmatic deep-search orchestration that uses existing helper modules.

    cache_path = _sanitize_cache_path(options.get("cache_path"))
    prompt_path = options.get("executive_summary_prompt_path", "")
    models = options.get("models", {})

    # Additional safeguard: warn if we dropped a suspicious cache_path value
    if options.get("cache_path") and cache_path is None:
        logger.warning(
            "Ignoring invalid cache_path value (looks like editor/settings content) "
            "instead of a filesystem path"
        )

    """
    options = options or {}
    collection = options.get("collection")
    limit = options.get("limit", 5)
    max_depth = options.get("max_depth", 2)
    cache_path = options.get("cache_path")
    prompt_path = options.get("executive_summary_prompt_path", "")
    model_dc = options.get("models", {})

    # Sanitize cache_path to avoid accidental editor/settings strings being used as filenames
    if isinstance(cache_path, str) and cache_path.strip().startswith(('"', "{", "[")):
        logger.warning(
            "Ignoring invalid cache_path value (looks like editor/settings content) "
            "instead of a filesystem path"
        )
        cache_path = None

    all_hit_ls = []

    for depth in range(max_depth):
        q = f"{request} (pass {depth+1})"
        logger.info(f"Searching (pass {depth+1}): {q}")
        try:
            result_ls = content_manager.search(q, max_results=limit) or []
        except Exception as e:
            # Catch FileNotFoundError and any other unexpected errors from the search layer
            logger.warning(f"Search failed on pass {depth+1} for query '{q}': {e}")
            continue

        for r in result_ls:
            url = r.get("url")
            if not url:
                continue
            logger.info(f"Fetching conversation: {url}")
            try:
                convo_dc = content_fetcher.fetch_github_conversation(url, cache_path=cache_path)
            except Exception as e:
                # Protect the orchestration from crashes due to bad cache_path or fetch errors
                logger.warning(f"Fetch failed for {url}: {e}")
                continue

            summary = ""
            try:
                if prompt_path:
                    summary = content_manager.summarize(url, prompt_path, cache_path=cache_path)
                else:
                    summary = f"Summary for {url} (no prompt provided)"
            except Exception as e:
                logger.warning(f"Summary failed for {url}: {e}")

            hit_dc = {
                "url": url,
                "summary": summary,
                "score": r.get("score", 0.9),
                "conversation": convo_dc,
            }
            all_hit_ls.append(hit_dc)

            # Optionally upsert to vector DB
            try:
                if collection:
                    content_manager.vector_upsert(
                        summary or url, collection, {"url": url}, model=model_dc.get("embed")
                    )
            except Exception as e:
                logger.warning(f"Vector upsert failed for {url}: {e}")

    report_dc = {
        "request": request,
        "results": all_hit_ls,
        "summary": f"Collected {len(all_hit_ls)} conversations",
    }
    return report_dc
