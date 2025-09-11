import os
from typing import Tuple

from ...clients.llm import llm_client
from ...pocketflow.pocketflow import Node
from ...utils.utils import get_logger

logger = get_logger(__name__)


class AnswererNode(Node):
    """Node that produces a final answer with staged retry strategy.

    Strategy (per user spec):
    1. First pass: full (uncompacted) context, base token limit.
    2. If finish_reason == 'length': retry with doubled token limit.
    3. If still 'length': compact context, keep doubled token limit and try again.
    4. If still failing or answer empty after these stages: raise RuntimeError.
    """

    # Defaults can be overridden via env vars.
    MAX_CONTEXT_CHARS = int(os.environ.get("ANSWERER_MAX_CONTEXT_CHARS", 8000))
    BASE_MAX_TOKENS = int(os.environ.get("ANSWERER_BASE_MAX_TOKENS", 1024))
    MAX_DOUBLED_TOKENS = int(os.environ.get("ANSWERER_MAX_DOUBLED_TOKENS", 2048))

    # --- internal helpers -------------------------------------------------
    def _compact_context(self, context: str) -> Tuple[str, bool]:
        """Heuristically compact context to a target size.

        Strategy:
        - If under limit, return unchanged.
        - Else attempt to keep the most recent SEARCH blocks (split on '\n\nSEARCH:').
        - Fall back to hard truncation with a notice header.

        Returns (compacted_context, was_compacted).
        """
        limit = self.MAX_CONTEXT_CHARS
        if len(context) <= limit:
            return context, False

        # Prefer most recent segments: split by SEARCH markers (retain order of most recent)
        parts = context.split("\n\nSEARCH:")
        # Reconstruct from the end backwards until within limit
        rebuilt_ls = []
        total = 0
        for segment in reversed(parts):
            seg = ("SEARCH:" + segment) if not segment.startswith("SEARCH:") else segment
            seg_len = len(seg)
            if total + seg_len > limit:
                break
            rebuilt_ls.append(seg)
            total += seg_len
        if rebuilt_ls:
            rebuilt = "\n\n".join(reversed(rebuilt_ls))
        else:
            rebuilt = context[-limit:]
        notice = (
            "[Context Compacted] Original context exceeded size limit; "
            "recent segments retained.\n"
        )
        return notice + rebuilt, True

    def _build_initial_prompt(self, question: str, compacted_context: str) -> str:
        return (
            "### CONTEXT\n"
            "Based on the following information, answer the question.\n"
            f"Question: {question}\n"
            f"Research: {compacted_context}\n\n"
            "## YOUR ANSWER:\n"
            "Provide a comprehensive yet concise answer grounded ONLY in the research.\n"
            "Return your response in this format:\n\n"
            "```yaml\n"
            "answer: <your comprehensive answer>\n"
            "```\n"
        )

    def _extract_finish_reason(self, response_dc) -> str:
        try:
            return response_dc.get("choices", [{}])[0].get("finish_reason").lower()
        except Exception:  # pragma: no cover
            return ""  # unknown

    def prep(self, shared):
        """Get the question, (possibly large) context, and verbosity flag."""
        return (
            shared["question"],
            shared.get("context", ""),
            shared.get("verbose", False),
        )

    def _call_llm(
        self,
        question: str,
        context: str,
        max_tokens: int,
        verbose: bool,
        stage: str,
    ) -> Tuple[str, str]:
        """Helper to call LLM and return (answer_text, finish_reason)."""
        prompt = self._build_initial_prompt(question, context)
        result_dc, response_dc = llm_client.generate(prompt, max_tokens=max_tokens)
        finish_reason = self._extract_finish_reason(response_dc)
        answer_text = result_dc.get("answer") or result_dc.get("fallback") or ""
        if verbose:
            logger.info(
                "Stage=%s finish_reason=%s answer_len=%s max_tokens=%s",
                stage,
                finish_reason,
                len(answer_text),
                max_tokens,
            )
        return answer_text, finish_reason

    def exec(self, inputs):
        question, context, verbose = inputs

        # Stage 1: full context
        answer_text, finish_reason = self._call_llm(
            question, context, self.BASE_MAX_TOKENS, verbose, stage="initial"
        )
        if finish_reason != "length" and answer_text.strip():
            return answer_text.strip()

        # Stage 2: double tokens (still full context) if truncated
        if finish_reason == "length":
            doubled_tokens = min(self.MAX_DOUBLED_TOKENS, self.BASE_MAX_TOKENS * 2)
            answer_text2, finish_reason2 = self._call_llm(
                question, context, doubled_tokens, verbose, stage="double_tokens"
            )
            if finish_reason2 != "length" and answer_text2.strip():
                return answer_text2.strip()
            # Stage 3: compact context + doubled tokens
            compacted_context, was_compacted = self._compact_context(context)
            if was_compacted:
                logger.info(
                    f"AnswererNode: context compacted from {len(context)} to {len(compacted_context)} chars for final attempt."  # noqa: E501
                )
            answer_text3, finish_reason3 = self._call_llm(
                question, compacted_context, doubled_tokens, verbose, stage="compact_context"
            )
            if finish_reason3 != "length" and answer_text3.strip():
                return answer_text3.strip()
            raise RuntimeError(
                "AnswererNode failed: truncated or empty answer after compacted retry."  # noqa: E501
            )

        # If not truncated but empty, raise.
        raise RuntimeError("AnswererNode failed: empty answer without truncation.")

    def post(self, shared, prep_res, exec_res):
        """Save the final answer and complete the flow."""
        shared["answer"] = exec_res
        if not shared.get("answer_ls"):
            shared["answer_ls"] = []
        shared["answer_ls"].append(exec_res)

        logger.info("✅ Answer generated successfully!")
