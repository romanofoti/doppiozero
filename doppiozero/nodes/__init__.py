# Node definitions for GitHubDeepResearchAgent
import logging
import json
from ..agent.pocketflow import Node
from ..agent.log import info


class InitialResearchNode(Node):
    def prep(self, shared):
        info("=== INITIAL RESEARCH PHASE ===")
        info(f"Starting initial semantic search for: {shared['request']}")
        return {"query": shared["request"]}

    def exec(self, plan):
        info("Executing initial semantic search and enriching results...")
        results = [
            {
                "url": "https://github.com/example/conversation/1",
                "summary": "Example summary",
                "score": 0.95,
                "conversation": {},
            }
        ]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = {"hits": exec_res, "notes": [], "search_queries": [shared["request"]]}
        info(f"✓ Initial research complete: {len(exec_res)} conversations collected")
        return None


class AskClarifyingNode(Node):
    def prep(self, shared):
        info("=== CLARIFYING QUESTIONS PHASE ===")
        return ["What is the main goal?", "Are there specific repos to focus on?"]

    def exec(self, questions):
        info("Presenting clarifying questions to user...")
        clarifications = "No further clarifications."
        return clarifications

    def post(self, shared, prep_res, exec_res):
        shared["clarifications"] = exec_res
        info("Clarifications stored.")
        return None


class PlannerNode(Node):
    def prep(self, shared):
        info("=== PLANNING PHASE ===")
        return {
            "semantic": {"query": shared["request"] + " implementation details"},
            "keyword": {"query": "repo:example is:issue"},
        }

    def exec(self, plan):
        info("Transforming queries into search plans...")
        return [
            {"tool": "semantic", "query": plan["semantic"]["query"]},
            {"tool": "keyword", "query": plan["keyword"]["query"]},
        ]

    def post(self, shared, prep_res, exec_res):
        shared["next_search_plans"] = exec_res
        info(f"✓ Planning complete, generated {len(exec_res)} search plans")
        return None


class RetrieverNode(Node):
    def prep(self, shared):
        info("=== RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        info("Executing search operations and retrieving data...")
        results = [
            {
                "url": "https://github.com/example/conversation/2",
                "summary": "Retrieved summary",
                "score": 0.90,
                "search_mode": "semantic",
                "conversation": {},
            }
        ]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["memory"]["hits"].extend(exec_res)
        shared["memory"]["search_queries"].append(", ".join([plan["query"] for plan in prep_res]))
        info(f"Added {len(exec_res)} new conversations to memory.")
        shared["current_depth"] = shared.get("current_depth", 0) + 1
        if shared["current_depth"] < shared["max_depth"]:
            return "continue"
        else:
            return "final"


class ParallelRetrieverNode(RetrieverNode):
    def prep(self, shared):
        info("=== PARALLEL RETRIEVAL PHASE ===")
        return shared.get("next_search_plans", [])

    def exec(self, search_plans):
        info("Executing parallel search operations...")
        results = [
            {
                "url": "https://github.com/example/conversation/3",
                "summary": "Parallel retrieved summary",
                "score": 0.92,
                "search_mode": "keyword",
                "conversation": {},
            }
        ]
        return results


class ContextCompactionNode(Node):
    def prep(self, shared):
        info("=== CONTEXT COMPACTION PHASE ===")
        return shared.get("memory", {})

    def exec(self, context):
        info("Compacting context for LLM constraints...")
        return context

    def post(self, shared, prep_res, exec_res):
        shared["memory"] = exec_res
        shared["compaction_attempts"] = shared.get("compaction_attempts", 0) + 1
        info("Context compaction complete.")
        return "retry"


class ClaimVerifierNode(Node):
    def prep(self, shared):
        info("=== CLAIM VERIFICATION PHASE ===")
        claims = ["Claim 1", "Claim 2"]
        return claims

    def exec(self, claims):
        info("Verifying claims against evidence...")
        results = [{"claim": claim, "supported": True} for claim in claims]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["claim_verification"] = {
            "total_claims": len(prep_res),
            "supported_claims": [r["claim"] for r in exec_res if r["supported"]],
            "unsupported_claims": [r["claim"] for r in exec_res if not r["supported"]],
            "verification_errors": 0,
        }
        info(f"✓ Claim verification complete: {len(exec_res)} claims checked.")
        if shared["claim_verification"]["unsupported_claims"]:
            return "fix"
        return "ok"


class ParallelClaimVerifierNode(ClaimVerifierNode):
    def prep(self, shared):
        info("=== PARALLEL CLAIM VERIFICATION PHASE ===")
        claims = ["Claim 1", "Claim 2"]
        return claims

    def exec(self, claims):
        info("Verifying claims in parallel...")
        results = [{"claim": claim, "supported": True} for claim in claims]
        return results


class FinalReportNode(Node):
    def exec(self, shared):
        info("Final report node: synthesizing findings into report.")
        return "complete"


class EndNode(Node):
    def exec(self, shared):
        info("End node: terminating workflow and returning results.")
        return None


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

    def call_llm(self, prompt, model):
        self.logger.debug(f"LLM called with model {model} and prompt length {len(prompt)}")
        return "# Final Markdown Report\n\n...LLM generated content..."

    def context_too_large_error(self, msg):
        return "context too large" in msg.lower()

    def rate_limit_error(self, msg):
        return "rate limit" in msg.lower()
