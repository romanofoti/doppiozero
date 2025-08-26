import json
import logging
from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
import logging


class FinalReportNode(Node):
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
        super().__init__()
        self.logger = logger or get_logger(__name__)
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
            # Safely obtain the reasoning model from shared configuration.
            # Use a sensible default model name when the key is missing so the
            # flow does not crash due to a KeyError. Downstream callers (e.g.
            # llm_client) will decide whether the model name maps to a real
            # provider or a deterministic stub.
            models_cfg = self.shared.get("models", {}) if self.shared else {}
            reasoning_model = models_cfg.get("reasoning", models_cfg.get("fast", "default"))
            if "reasoning" not in models_cfg:
                self.logger.debug(
                    f"No explicit reasoning model configured; falling back to '{reasoning_model}'"
                )
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
            self.logger.info(
                f"**Note**: The following {len(shared['unsupported_claims'])} claims could not be fully verified against the available evidence:"
            )
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
            verification_note = f", {cv['total_claims']} claims verified ({len(cv['supported_claims'])} supported, {len(cv['unsupported_claims'])} unsupported)"
        self.logger.info(
            f"\n\n✓ Research complete! Total conversations analyzed: {len(shared['memory']['hits'])}{compaction_note}{verification_note}"
        )
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
        self.logger.debug(f"LLM called with model {model} and prompt length {len(prompt)}")
        return "# Final Markdown Report\n\n...LLM generated content..."

    def context_too_large_error(self, msg):
        return "context too large" in msg.lower()

    def rate_limit_error(self, msg):
        return "rate limit" in msg.lower()
