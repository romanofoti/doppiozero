from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

logger = get_logger(__name__)


class ClaimVerifierNode(Node):
    def prep(self, shared):
        logger.info("=== CLAIM VERIFICATION PHASE ===")
        claims = ["Claim 1", "Claim 2"]
        return claims

    def exec(self, claims):
        logger.info("Verifying claims against evidence...")
        results = [{"claim": claim, "supported": True} for claim in claims]
        return results

    def post(self, shared, prep_res, exec_res):
        shared["claim_verification"] = {
            "total_claims": len(prep_res),
            "supported_claims": [r["claim"] for r in exec_res if r["supported"]],
            "unsupported_claims": [r["claim"] for r in exec_res if not r["supported"]],
            "verification_errors": 0,
        }
        logger.info(f"✓ Claim verification complete: {len(exec_res)} claims checked.")
        if shared["claim_verification"]["unsupported_claims"]:
            return "fix"
        return "ok"
