from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..clients.llm import llm_client
from ..contents import content_manager
from typing import List, Dict
import re
import json
import os

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
        # Keep shared on the instance for use in exec/helpers (upstream pattern)
        self.shared = shared
        # Try to extract claims from a draft report if available.
        # Use upstream-style prompt template when possible.
        draft = shared.get("draft_answer") or shared.get("final_report", {}).get("draft")
        if draft and llm_client:
            try:
                claims = self.extract_claims_from_report(
                    draft, shared.get("models", {}).get("fast")
                )
                if claims:
                    logger.info("Extracted %d claims from draft.", len(claims))
                    return claims
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

            # Use search_evidence_for_claim to build formatted evidence text
            evidence_text = self.search_evidence_for_claim(
                claim, collection, None, limit=max_evidence
            )

            # Use LLM to verify claim against evidence; expects single-word response
            is_supported = False
            try:
                model_name = getattr(self, "shared", {}).get("models", {}).get("fast")
                is_supported = self.verify_claim_against_evidence(
                    claim, evidence_text, shared_model=model_name
                )
            except Exception as e:
                logger.debug("Verification LLM failed for claim '%s': %s", claim, e)

            if is_supported:
                results.append(
                    {
                        "claim": claim,
                        "status": "supported",
                        "evidence": evidence,
                        "reasoning": "supported_by_evidence",
                    }
                )
                logger.info("\u2713 Claim supported: %s", claim[:120])
            else:
                results.append(
                    {
                        "claim": claim,
                        "status": "unsupported",
                        "evidence": evidence,
                        "reasoning": "no_support_found",
                    }
                )
                logger.info("\u2717 Claim unsupported: %s", claim[:120])

        return results

    # --- Helper methods to mirror upstream node behavior ---
    def _normalize_llm_text(self, resp):
        """Normalize the output from llm_client.generate into a string.

        Handles cases where the client returns (str) or (dict, raw) tuples.
        """
        if resp is None:
            return ""
        # If the client returns a tuple (result_dc, raw_dc)
        if isinstance(resp, tuple) or isinstance(resp, list):
            first = resp[0] if len(resp) > 0 else resp
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                # Try common fallback keys
                if "fallback" in first:
                    return str(first["fallback"]) or ""
                try:
                    return json.dumps(first)
                except Exception:
                    return str(first)
        if isinstance(resp, dict):
            # Try to extract known content keys
            if "choices" in resp and isinstance(resp["choices"], list):
                try:
                    return resp["choices"][0]["message"]["content"]
                except Exception:
                    pass
            return json.dumps(resp)
        return str(resp)

    def extract_claims_from_report(self, report: str, model: str = None) -> List[str]:
        """Extract claims from a report using a structured prompt and JSON parsing.

        Returns a list of claim strings (max 25) or an empty list on failure.
        """
        # Try to load EXTRACT_CLAIMS_PROMPT from local prompts if available
        try:
            cwd = os.getcwd()
            prompt_path = os.path.join(cwd, "prompts", "refine", "extract_claims.md")
            if os.path.isfile(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt = f.read()
            else:
                # Inline prompt similar to upstream
                prompt = (
                    "You are tasked with extracting factual claims from a research report.\n\n"
                    "Return ONLY a JSON array of claim strings (max 25).\n\nReport:\n{{report}}"
                )
            filled = prompt.replace("{{report}}", report)
            resp = llm_client.generate(filled, model=model)
            raw = self._normalize_llm_text(resp)

            # Remove code fences commonly emitted by LLMs
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = re.sub(r"\A```json\s*", "", cleaned)
                cleaned = re.sub(r"\s*```\Z", "", cleaned)
            elif cleaned.startswith("```"):
                cleaned = re.sub(r"\A```\s*", "", cleaned)
                cleaned = re.sub(r"\s*```\Z", "", cleaned)

            # Parse JSON array
            try:
                parsed = json.loads(cleaned.strip())
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed][:25]
            except Exception:
                return []
        except Exception:
            return []

    def verify_claim_against_evidence(
        self, claim: str, evidence: str, model: str = None, shared_model: str = None
    ) -> bool:
        """Verify a single claim against evidence using the VERIFY_CLAIM_PROMPT semantics.

        Returns True when LLM says SUPPORTED, False otherwise. Falls back to
        heuristic (high score) if available.
        """
        model_to_use = model or shared_model
        try:
            # Load prompt if present
            cwd = os.getcwd()
            prompt_path = os.path.join(cwd, "prompts", "refine", "verify_claim.md")
            if os.path.isfile(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt = f.read()
            else:
                prompt = (
                    "You are a fact-checker tasked with verifying a claim against "
                    "provided evidence.\n\nClaim:\n{{claim}}\n\nEvidence:\n{{evidence}}\n\n"
                    "Respond with exactly one word: SUPPORTED or UNSUPPORTED"
                )
            filled = prompt.replace("{{claim}}", claim).replace("{{evidence}}", evidence)
            resp = llm_client.generate(filled, model=model_to_use)
            raw = self._normalize_llm_text(resp)
            result = raw.strip().upper()
            # Extract single word if surrounded by text
            m = re.search(r"(SUPPORTED|UNSUPPORTED)", result)
            if m:
                return m.group(1) == "SUPPORTED"
            # Default conservative behavior: unsupported
            return False
        except Exception:
            return False

    def search_evidence_for_claim(
        self, claim: str, collection: str, script_dir: str = None, limit: int = 3
    ) -> str:
        """Search for evidence using the ContentManager and format results for LLM.

        Returns a joined evidence string suitable to pass into verification prompt.
        """
        try:
            hits = content_manager.vector_search(claim, collection=collection, top_k=limit)
            if not hits:
                return "No relevant evidence found."
            parts = []
            for i, r in enumerate(hits):
                url = r.get("url") or "Unknown URL"
                summary = r.get("summary") or "No summary available"
                score = r.get("score") or 0.0
                parts.append(
                    (
                        f"Evidence {i+1} (Score: {float(score):.3f}):\n"
                        f"Source: {url}\nSummary: {summary}"
                    )
                )
            return "\n\n---\n\n".join(parts)
        except Exception as e:
            return f"Error retrieving evidence: {e}"

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
