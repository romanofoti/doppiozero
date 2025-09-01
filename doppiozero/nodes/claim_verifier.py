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
        # Try to extract claims from a draft report if available.
        # Use a configurable prompt or default extraction via the LLM.
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

        # Configuration
        top_k = int(self.params.get("top_k", 5))
        collection = self.params.get("collection", "default")
        max_evidence = int(self.params.get("max_evidence", 5))

        for claim in claims:
            # Retrieve candidate evidence via semantic search
            try:
                hits = content_manager.vector_search(claim, collection=collection, top_k=top_k)
            except Exception as e:
                logger.debug("Vector search failed for claim '%s': %s", claim, e)
                hits = []

            # Build evidence list with snippets and sources
            evidence = []
            for h in (hits or [])[:max_evidence]:
                snippet = h.get("summary") or str(h.get("conversation", {}))[:400]
                evidence.append(
                    {"source": h.get("url"), "snippet": snippet, "score": h.get("score")}
                )

            # Default classification
            status = "insufficient"
            reasoning = ""

            # Structured LLM classification: expect JSON with {status, reasoning}
            if llm_client:
                try:
                    ev_text = "\n\n".join(
                        [f"Source: {e['source']}\nSnippet: {e['snippet']}" for e in evidence]
                    )
                    classify_prompt = (
                        f"You are an assistant that judges whether an evidence set supports "
                        f"a factual claim.\nClaim:\n{claim}\n\nEvidence:\n{ev_text}\n\n"
                        'Respond only with a JSON object like {"status": "supported"|'
                        '"contradicted"|"insufficient", "reasoning": "..."}.'
                    )
                    raw = llm_client.generate(classify_prompt)
                    import json

                    # Try to parse the model output; tolerate surrounding text by
                    # finding the first JSON substring.
                    parsed = None
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        # Attempt to extract JSON object substring
                        import re

                        m = re.search(r"\{.*\}", raw, re.S)
                        if m:
                            try:
                                parsed = json.loads(m.group(0))
                            except Exception:
                                parsed = None

                    if parsed and isinstance(parsed, dict):
                        status = parsed.get("status", status)
                        reasoning = parsed.get("reasoning", reasoning)
                except Exception as e:
                    logger.debug("LLM classification failed for claim '%s': %s", claim, e)

            # Heuristic fallback when LLM is unavailable or fails
            if status == "insufficient":
                if any((e.get("score") or 0) > 0.75 for e in evidence):
                    status = "supported"
                    reasoning = "High-scoring matching evidence found."

            results.append(
                {"claim": claim, "status": status, "evidence": evidence, "reasoning": reasoning}
            )

        return results

    def exec_fallback(self, prep_res, exc):
        """Fallback used when exec raises: mark claims as inconclusive."""
        logger.error("Verifier exec failed: %s", exc)
        out = []
        for c in prep_res or []:
            out.append(
                {
                    "claim": c,
                    "status": "insufficient",
                    "evidence": [],
                    "reasoning": "verifier_error",
                }
            )
        return out

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
