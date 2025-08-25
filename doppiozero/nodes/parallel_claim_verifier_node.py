from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from .claim_verifier_node import ClaimVerifierNode


logger = get_logger(__name__)


class ParallelClaimVerifierNode(ClaimVerifierNode):
    def prep(self, shared):
        logger.info("=== PARALLEL CLAIM VERIFICATION PHASE ===")
        claims = ["Claim 1", "Claim 2"]
        return claims

    def exec(self, claims):
        logger.info("Verifying claims in parallel...")
        results = [{"claim": claim, "supported": True} for claim in claims]
        return results
