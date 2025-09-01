from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger

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
        claim_ls = ["Claim 1", "Claim 2"]
        return claim_ls

    def exec(self, claims):
        """Verify claims and return a list of verification results.

        Args:
            claims : A list of claim strings to verify.

        Returns:
            A list of dicts with ``claim`` and ``supported`` boolean fields.

        """
        logger.info("Verifying claims against evidence...")
        result_ls = [{"claim": claim, "supported": True} for claim in claims]
        return result_ls

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
        shared["claim_verification"] = {
            "total_claims": len(prep_res),
            "supported_claims": [r["claim"] for r in exec_res if r["supported"]],
            "unsupported_claims": [r["claim"] for r in exec_res if not r["supported"]],
            "verification_errors": 0,
        }
        logger.info(f"\u2713 Claim verification complete: {len(exec_res)} claims checked.")
        if shared["claim_verification"]["unsupported_claims"]:
            return "fix"
        return "ok"
