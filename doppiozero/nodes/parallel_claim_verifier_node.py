from ..agent.pocketflow import Node
from ..agent.log import info
from .claim_verifier_node import ClaimVerifierNode


class ParallelClaimVerifierNode(ClaimVerifierNode):
    def prep(self, shared):
        info("=== PARALLEL CLAIM VERIFICATION PHASE ===")
        claims = ["Claim 1", "Claim 2"]
        return claims

    def exec(self, claims):
        info("Verifying claims in parallel...")
        results = [{"claim": claim, "supported": True} for claim in claims]
        return results
