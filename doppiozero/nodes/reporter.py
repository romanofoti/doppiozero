import json
from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger


class FinalReportNode(Node):
    FINAL_REPORT_PROMPT = (
        "You are an expert analyst preparing a comprehensive report.\n"
        "## Original Request\n{{request}}\n"
        "## User Clarifications\n{{clarifications}}\n"
        "## Research Corpus\n{{all_findings}}\n"
        "Produce a clear, well-structured Markdown report.\n"
        "Cite relevant sources used to support findings.\n"
        "**Style guide**\n"
        "* Use proper Markdown headings (`##`, `###`).\n"
        "* Omit horizontal rules.\n"
        "* Back factual claims with inline citations (full URL).\n"
        "* If a status cannot be confirmed, mark it as **Unknown**.\n"
        "Return only the Markdown document; no extra commentary."
    )

    """Node that generates a comprehensive final Markdown report.

    The final report node gathers all findings from shared memory. It
    builds a prompt using a static template and calls an LLM to produce
    the final Markdown report. It handles errors related to context size
    and rate limits and records metadata about the final report in
    shared state.

    """

    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or get_logger(__name__)
        self.shared = None

    # NOTE: the real prep implementation is defined below. The empty
    # stub that used to appear here was duplicated during an earlier
    # docstring pass and caused a redefinition error (F811). It's
    # deliberately removed to keep a single canonical implementation.

    def prep(self, shared):
        """Prepare the LLM prompt by aggregating findings from shared memory.

        Args:
            shared : The shared flow state containing memory, clarifications,
                     and other metadata collected during the flow.

        Returns:
            The fully rendered prompt string to send to the LLM.

        """
        self.shared = shared
        self.logger.info("=== FINAL REPORT PHASE ===")
        self.logger.info("Generating final report from all gathered data...")

        compaction_note = ""
        compaction_attempts = shared.get("compaction_attempts", 0)
        if compaction_attempts > 0:
            compaction_note = f" (after {compaction_attempts} context compaction attempts)"

        num_hits = len(shared.get("memory", {}).get("hits", []))
        num_queries = len(shared.get("memory", {}).get("search_queries", []))
        depth = shared.get("current_depth", 0)
        # Build a concise research summary in smaller parts to avoid
        # excessively long single lines and to satisfy line-length
        # linter rules.
        summary_parts_ls = [
            f"Research summary: {num_hits} conversations analyzed{compaction_note},",
            f"{num_queries} queries used, {depth} deep research iterations",
        ]
        summary_msg = " ".join(summary_parts_ls)
        self.logger.info(summary_msg)

        # Build a readable sources list
        sources_ls = []
        for i, hit in enumerate(shared.get("memory", {}).get("hits", [])):
            url = hit.get("url")
            score = hit.get("score")
            sources_ls.append(f"  {i + 1}. {url} (score: {score})")
        sources_list = "\n".join(sources_ls)
        self.logger.debug("All conversation sources:\n%s", sources_list)

        # Build findings payload by iterating to avoid overly long one-liners
        findings_parts_ls = []
        for hit in shared.get("memory", {}).get("hits", []):
            src = hit.get("url")
            summary = hit.get("summary")
            score = hit.get("score")
            convo = json.dumps(hit.get("conversation", {}), indent=2)
            part = (
                f"**Source**: {src}\n"
                f"**Summary**: {summary}\n"
                f"**Relevance Score**: {score}\n"
                f"**Conversation Details**:\n{convo}"
            )
            findings_parts_ls.append(part)

        all_findings = "\n\n---\n\n".join(findings_parts_ls)

        prompt = self.FINAL_REPORT_PROMPT.replace("{{request}}", str(shared.get("request", "")))
        prompt = prompt.replace(
            "{{clarifications}}", str(shared.get("clarifications", "None provided"))
        )
        prompt = prompt.replace("{{all_findings}}", all_findings)

        self.logger.debug("Calling LLM to generate final report...")
        return prompt

    def exec(self, prompt):
        """Generate the final report using an LLM.

        Chooses a reasoning model from shared configuration when available
        and falls back to a sensible default. Stores the draft under
        ``draft_answer`` in shared state. If the call fails due to
        context size or rate limits, returns the control token
        "context_too_large" to trigger compaction or retries.

        Args:
            prompt: Prompt string prepared in :meth:`prep`.

        Returns:
            The generated draft report string, or "context_too_large".

        """
        try:
            # Safely obtain the reasoning model from shared configuration.
            # Use a sensible default model name when the key is missing so the
            # flow does not crash due to a KeyError. Downstream callers (e.g.
            # llm_client) will decide whether the model name maps to a real
            # provider or a deterministic stub.
            models_cfg = self.shared.get("models", {}) if self.shared else {}
            reasoning_model = models_cfg.get("reasoning", models_cfg.get("fast", "default"))
            if "reasoning" not in models_cfg:
                _msg = ("No explicit reasoning model configured; " "falling back to '{m}'").format(
                    m=reasoning_model
                )
                self.logger.debug(_msg)
            draft_answer = self.call_llm(prompt, reasoning_model)
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
        self.logger.info(exec_res)
        if shared.get("unsupported_claims"):
            self.logger.info("\n\n---\n\n")
            note_msg = (
                "**Note**: The following "
                f"{len(shared['unsupported_claims'])} claims could not be fully "
                "verified against the available evidence:"
            )
            self.logger.info(note_msg)
            for i, claim in enumerate(shared["unsupported_claims"]):
                self.logger.info(f"{i + 1}. {claim}")
        compaction_note = ""
        if shared.get("compaction_attempts", 0) > 0:
            compaction_note = (
                f" (after {shared['compaction_attempts']} context compaction attempts)"
            )
        verification_note = ""
        if shared.get("claim_verification"):
            cv = shared["claim_verification"]
            verification_note = (", {} claims verified ({} supported, {} unsupported)").format(
                cv["total_claims"],
                len(cv.get("supported_claims", [])),
                len(cv.get("unsupported_claims", [])),
            )
        total_msg = "\n\n✓ Research complete! Total conversations analyzed: "
        total_msg += str(len(shared["memory"]["hits"]))
        if compaction_note:
            total_msg += compaction_note
        if verification_note:
            total_msg += verification_note
        self.logger.info(total_msg)
        # Store a structured final report in shared state so the EndNode can
        # return it to the caller. Keep both the raw draft and useful metadata.
        shared.setdefault("final_report", {})
        shared["final_report"].update(
            {
                "draft": exec_res,
                "num_conversations": len(shared["memory"]["hits"]),
                "claims_verified": len(
                    shared.get("claim_verification", {}).get("supported_claims", [])
                ),
                "unsupported_claims": shared.get("unsupported_claims", []),
            }
        )
        return "complete"

    def call_llm(self, prompt, model):
        """Helper that performs the LLM call.

        In the default implementation this is a stub that returns a placeholder
        Markdown string. Production implementations may proxy to a real LLM
        client.

        Args:
            prompt : The prompt to send to the model.
            model : The model identifier to use for the call.

        Returns:
            The LLM-generated draft of the final report.

        """
        self.logger.debug(f"LLM called with model {model} and prompt length {len(prompt)}")
        return "# Final Markdown Report\n\n...LLM generated content..."

    def context_too_large_error(self, msg):
        """Return True when the message indicates the model's context is too large.

        Args:
            msg : The exception message text to inspect.

        Returns:
            True when the message signals the context is too large.

        """
        return "context too large" in msg.lower()

    def rate_limit_error(self, msg):
        """Return True when the message indicates a rate limit was hit.

        Args:
            msg : The exception message text to inspect.

        Returns:
            True when the message signals a rate limit error.

        """
        return "rate limit" in msg.lower()
