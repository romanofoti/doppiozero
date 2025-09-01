from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..clients.llm import llm_client
from ..contents import content_manager
from typing import List, Dict

logger = get_logger(__name__)


class VerifierNode(Node):
    """Node that verifies claims against available evidence.

    Parameters
    ----------
    None

    Attributes
    ----------
    logger : logging.Logger
        Module-level logger obtained via :func:`doppiozero.utils.utils.get_logger`.
    Inherits attributes from :class:`pocketflow.pocketflow.Node`.

    Notes
    -----
    This node prepares a list of claims, verifies them (synchronously), and
    records verification results into the shared flow state.

    """

    def prep(self, shared):
        """Prepare a list of claims to verify.

        Args:
            shared : Shared flow state (unused here but provided for API consistency).

        Returns:
            A list of claim strings to be verified.

        """
        logger.info("=== CLAIM VERIFICATION PHASE ===")
        # Try to extract claims from a draft report if available
        draft = shared.get("draft_answer") or shared.get("final_report", {}).get("draft")
        if draft and llm_client:
            try:
                prompt = (
                    "Extract the key factual claims from the following report. "
                    "Return a JSON array of short claim strings.\n\nReport:\n" + str(draft)
                )
                raw = llm_client.generate(prompt)
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    claim_ls = [str(c).strip() for c in parsed if c]
                    logger.info("Extracted %d claims from draft.", len(claim_ls))
                    return claim_ls
            except Exception as e:
                logger.debug("Claim extraction failed: %s", e)
        # Fallback: use provided claims in shared or simple placeholders
        shared_claims = shared.get("claims")
        if shared_claims:
            return list(shared_claims)
        return ["Claim 1", "Claim 2"]

    def exec(self, claims):
        """Verify claims and return a list of verification results.

        Args:
            claims : A list of claim strings to verify.

        Returns:
            A list of dicts with ``claim`` and ``supported`` boolean fields.

        """
        logger.info("Verifying %d claims against evidence...", len(claims))
        results: List[Dict] = []
        for claim in claims:
            # Retrieve candidate evidence via semantic search
            try:
                hits = content_manager.vector_search(claim, collection="default", top_k=5)
            except Exception as e:
                logger.debug("Vector search failed for claim '%s': %s", claim, e)
                hits = []

            # Build evidence list with snippets and sources
            evidence = []
            for h in hits[:5]:
                snippet = h.get("summary") or (str(h.get("conversation", {}))[:400])
                evidence.append(
                    {"source": h.get("url"), "snippet": snippet, "score": h.get("score")}
                )

            # Ask LLM to classify the claim given evidence
            status = "insufficient"
            reasoning = ""
            if llm_client:
                try:
                    ev_text = "\n\n".join(
                        [f"Source: {e['source']}\nSnippet: {e['snippet']}" for e in evidence]
                    )
                    classify_prompt = (
                        f"Given the claim:\n{claim}\n\nAnd the following evidence:\n{ev_text}\n\n"
                        'Answer with a JSON object {"status": <supported|contradicted|'
                        'insufficient>, "reasoning": <string>} explaining whether the '
                        "evidence supports the claim."
                    )
                    raw = llm_client.generate(classify_prompt)
                    import json

                    parsed = json.loads(raw)
                    status = parsed.get("status", "insufficient")
                    reasoning = parsed.get("reasoning", "")
                except Exception as e:
                    logger.debug("LLM classification failed for claim '%s': %s", claim, e)
                    # Default heuristic: supported if any high-score evidence
                    if any((e.get("score") or 0) > 0.75 for e in evidence):
                        status = "supported"
                        reasoning = "High-scoring matching evidence found."

            results.append(
                {"claim": claim, "status": status, "evidence": evidence, "reasoning": reasoning}
            )

        return results

    def post(self, shared, prep_res, exec_res):
        """Record verification summary into shared state and return next action.

        Args:
            shared : Shared flow state to update.
            prep_res : The claims that were verified.
            exec_res : The verification results returned by :meth:`exec`.

        Returns:
            A token indicating the flow's next step. Returns "fix" if there are
            unsupported claims, otherwise "ok".

        """
        # Normalize results into shared state
        supported = [r["claim"] for r in exec_res if r.get("status") == "supported"]
        unsupported = [r["claim"] for r in exec_res if r.get("status") == "contradicted"]
        insufficient = [r["claim"] for r in exec_res if r.get("status") == "insufficient"]
        shared["claim_verification"] = {
            "total_claims": len(prep_res),
            "supported_claims": supported,
            "unsupported_claims": unsupported,
            "insufficient_claims": insufficient,
            "verification_errors": 0,
            "details": exec_res,
        }
        logger.info("\u2713 Claim verification complete: %d claims checked.", len(exec_res))
        # Expose a convenience list for downstream nodes
        shared["unsupported_claims"] = unsupported
        if unsupported or insufficient:
            # If any claims need fixing or lack evidence, request a fix/verification
            return "fix"
        return "ok"
