"""
GitHubDeepResearchAgent - Multi-Stage Research Pipeline for GitHub Conversations (Python)
"""

from ..agent.pocketflow import Node, Flow
from ..agent.utils import setup_logger
from ..agent.log import info, warn, error


# Node definitions (stubs, to be implemented)
class InitialResearchNode(Node):
    def exec(self, shared):
        info("Initial research node: bootstrapping context.")
        return "clarify"


class AskClarifyingNode(Node):
    def exec(self, shared):
        info("Ask clarifying node: generating clarifying questions.")
        return "plan"


class PlannerNode(Node):
    def exec(self, shared):
        info("Planner node: decomposing research question and planning next step.")
        return "retrieve"


class RetrieverNode(Node):
    def exec(self, shared):
        info("Retriever node: executing search plan and fetching conversations.")
        # Simulate branching: continue for more, final for report
        return "final" if shared.get("done") else "continue"


class ParallelRetrieverNode(RetrieverNode):
    def exec(self, shared):
        info("Parallel retriever node: concurrent search execution.")
        return super().exec(shared)


class ContextCompactionNode(Node):
    def exec(self, shared):
        info("Context compaction node: pruning context for LLM/memory constraints.")
        return "retry"


class ClaimVerifierNode(Node):
    def exec(self, shared):
        info("Claim verifier node: verifying claims/hypotheses.")
        return "ok"


class ParallelClaimVerifierNode(ClaimVerifierNode):
    def exec(self, shared):
        info("Parallel claim verifier node: concurrent verification.")
        return super().exec(shared)


class FinalReportNode(Node):
    def exec(self, shared):
        info("Final report node: synthesizing findings into report.")
        return "complete"


class EndNode(Node):
    def exec(self, shared):
        info("End node: terminating workflow and returning results.")
        return None


class FinalReportNode(Node):
    """
    Synthesizes research findings into a comprehensive Markdown report.
    Handles context compaction, error recovery, and integrates claim verification before final output.
    """

    FINAL_REPORT_PROMPT = (
        "You are an expert analyst preparing a comprehensive Markdown report.\n"
        "## Original Request\n{{request}}\n"
        "## User Clarifications\n{{clarifications}}\n"
        "## Research Corpus\n{{all_findings}}\n"
        "Produce a well-structured Markdown report based on the initial request and clarifications and cite relevant sources used to support your findings.\n"
        "**Style guide**\n"
        "* Use proper Markdown headings (`##`, `###`) and omit horizontal rules (`---`).\n"
        "* Every factual claim must be backed by an inline citation (full URL).\n"
        "* If status cannot be confirmed, mark it **Unknown** and note what evidence is missing.\n"
        "Return only the Markdown document—no extra commentary."
    )

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.shared = None

    def prep(self, shared):
        self.shared = shared
        self.logger.info("=== FINAL REPORT PHASE ===")
        self.logger.info("Generating final report from all gathered data...")
        compaction_note = ""
        if shared.get("compaction_attempts", 0) > 0:
            compaction_note = (
                f" (after {shared['compaction_attempts']} context compaction attempts)"
            )
        self.logger.info(
            f"Research summary: {len(shared['memory']['hits'])} conversations analyzed{compaction_note}, {len(shared['memory']['search_queries'])} queries used, {shared.get('current_depth', 0)} deep research iterations"
        )
        sources_list = "\n".join(
            [
                f"  {i + 1}. {hit['url']} (score: {hit['score']})"
                for i, hit in enumerate(shared["memory"]["hits"])
            ]
        )
        self.logger.debug(f"All conversation sources:\n{sources_list}")
        all_findings = "\n\n---\n\n".join(
            [
                f"**Source**: {hit['url']}\n**Summary**: {hit['summary']}\n**Relevance Score**: {hit['score']}\n**Conversation Details**:\n{json.dumps(hit['conversation'], indent=2)}"
                for hit in shared["memory"]["hits"]
            ]
        )
        prompt = (
            self.FINAL_REPORT_PROMPT.replace("{{request}}", str(shared.get("request", "")))
            .replace("{{clarifications}}", str(shared.get("clarifications", "None provided")))
            .replace("{{all_findings}}", all_findings)
        )
        self.logger.debug("Calling LLM to generate final report...")
        return prompt

    def exec(self, prompt):
        try:
            # Use reasoning model for final report generation
            # This requires complex analysis and synthesis of all gathered data
            draft_answer = self.call_llm(prompt, self.shared["models"]["reasoning"])
            self.shared["draft_answer"] = draft_answer
            return draft_answer
        except Exception as e:
            msg = str(e)
            if self.context_too_large_error(msg) or self.rate_limit_error(msg):
                if self.rate_limit_error(msg):
                    self.logger.warning(f"Rate limit encountered: {msg}")
                    self.logger.info(
                        "Will attempt to compact context to reduce token usage and retry..."
                    )
                else:
                    self.logger.warning(f"Context too large for model: {msg}")
                    self.logger.info("Will attempt to compact context and retry...")
                self.shared["last_context_error"] = msg
                return "context_too_large"
            else:
                self.logger.error(f"Unexpected error during final report generation: {msg}")
                raise

    def post(self, shared, prep_res, exec_res):
        if exec_res == "context_too_large":
            self.logger.info("Context too large, routing to compaction...")
            return "compact"
        if not shared.get("claim_verification_completed"):
            self.logger.info("Routing to claim verification before final output")
            shared["claim_verification_completed"] = True
            return "verify"
        self.logger.info("=== FINAL REPORT ===\n\n")
        print(exec_res)
        if shared.get("unsupported_claims"):
            print("\n\n---\n\n")
            print(
                f"**Note**: The following {len(shared['unsupported_claims'])} claims could not be fully verified against the available evidence:"
            )
            for i, claim in enumerate(shared["unsupported_claims"]):
                print(f"{i + 1}. {claim}")
        compaction_note = ""
        if shared.get("compaction_attempts", 0) > 0:
            compaction_note = (
                f" (after {shared['compaction_attempts']} context compaction attempts)"
            )
        verification_note = ""
        if shared.get("claim_verification"):
            cv = shared["claim_verification"]
            verification_note = f", {cv['total_claims']} claims verified ({len(cv['supported_claims'])} supported, {len(cv['unsupported_claims'])} unsupported)"
        self.logger.info(
            f"\n\n✓ Research complete! Total conversations analyzed: {len(shared['memory']['hits'])}{compaction_note}{verification_note}"
        )
        return "complete"

    # --- Utility methods ---
    def call_llm(self, prompt, model):
        # Placeholder for LLM call
        # Replace with actual LLM integration
        self.logger.debug(f"LLM called with model {model} and prompt length {len(prompt)}")
        return "# Final Markdown Report\n\n...LLM generated content..."

    def context_too_large_error(self, msg):
        return "context too large" in msg.lower()

    def rate_limit_error(self, msg):
        return "rate limit" in msg.lower()


class EndNode(Node):
    def exec(self, shared):
        info("End node: terminating workflow and returning results.")
        return None


def start_github_deep_research_agent(request, options=None):
    options = options or {}
    logger = setup_logger("agent")

    if not request or not request.strip():
        raise ValueError("Empty request provided")
    if "collection" not in options:
        raise ValueError("Collection is required")

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

    flow.run(shared)
