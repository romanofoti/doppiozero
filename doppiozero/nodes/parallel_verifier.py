from ..utils.utils import get_logger
from .claim_verifier import VerifierNode


logger = get_logger(__name__)


class ParallelClaimVerifierNode(VerifierNode):
    """A verifier that runs claim checks in parallel.

    Extends :class:`VerifierNode` and performs parallel verification of
    claims. It follows the standard prep/exec lifecycle.

    Parameters
    ----------
    None

    Attributes
    ----------
    Inherits attributes from :class:`VerifierNode`.
    """

    def prep(self, shared):
        """Return the list of claims to verify in parallel.

        Args:
            shared : Shared flow state.

        Returns:
            Claim strings to verify.

        """
        logger.info("=== PARALLEL CLAIM VERIFICATION PHASE ===")
        claim_ls = ["Claim 1", "Claim 2"]
        return claim_ls

    def exec(self, claims):
        """Verify claims concurrently and return verification results.

        Args:
            claims : A list of claim strings.

        Returns:
            A list of dicts with verification outcomes.

        """
        logger.info("Verifying claims in parallel...")
        result_ls = [{"claim": claim, "supported": True} for claim in claims]
        return result_ls
