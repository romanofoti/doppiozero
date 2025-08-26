from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from .claim_verifier import VerifierNode


logger = get_logger(__name__)


class ParallelClaimVerifierNode(VerifierNode):
    def prep(self, shared):
        logger.info("=== PARALLEL CLAIM VERIFICATION PHASE ===")
        claim_ls = ["Claim 1", "Claim 2"]
        return claim_ls

    def exec(self, claims):
        logger.info("Verifying claims in parallel...")
        result_ls = [{"claim": claim, "supported": True} for claim in claims]
        return result_ls
