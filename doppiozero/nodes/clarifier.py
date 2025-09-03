from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger, edit_text
from ..clients.llm import llm_client
import os
import json

logger = get_logger(__name__)


class ClarifierNode(Node):
    """Node that generates and processes clarifying questions.

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
    This node generates clarifying questions and stores user-provided
    clarifications in the shared state under the ``clarifications`` key.

    """

    def prep(self, shared):
        """Return a list of clarifying questions to present to the user.

        Args:
            shared : Shared flow state (unused by this preparer but provided for API consistency).

        Returns:
            A list of question strings to ask the user.

        """
        logger.info("=== CLARIFYING QUESTIONS PHASE ===")
        self.shared = shared

        # If clarifications already exist, don't ask again.
        if shared.get("clarifications"):
            logger.debug("Clarifications already present; skipping question generation.")
            return []

        # Default question set when LLM is not available or returns nothing
        # Use the project's naming convention for lists: suffix with `_ls`.
        default_q_ls = ["What is the main goal?", "Are there specific repos to focus on?"]

        # Build initial findings summary from shared memory (upstream parity)
        initial_findings = ""
        try:
            hits_ls = shared.get("memory", {}).get("hits", [])
            lines_ls = []
            for hit in hits_ls:
                u = hit.get("url")
                s = hit.get("summary") or ""
                lines_ls.append(f"- {u}: {s}")
            initial_findings = "\n".join(lines_ls)
        except Exception:
            initial_findings = ""

        # Try to load upstream-style ASK_CLARIFY_PROMPT from prompts/ if present
        prompt_text = None
        # Try prompts/ask_clarify(.md|.txt)
        cwd = os.getcwd()
        for candidate in ("ask_clarify", "ask_clarify.md", "ask_clarify.txt"):
            p = os.path.join(cwd, "prompts", "refine", candidate)
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        prompt_text = f.read()
                        break
                except Exception:
                    prompt_text = None

        # Fallback inlined prompt (keeps parity with upstream instructions)
        if not prompt_text:
            prompt_text = (
                "You are an expert analyst reviewing a research request and initial findings.\n\n"
                "## Research Request\n{{request}}\n\n## Initial Findings\n{{initial_findings}}\n\n"
                "Based on the question and initial findings, generate up to 4 clarifying questions "
                "that would help you better understand the intent of the request, "
                "bridge gaps in context, and understand the expected output format. "
                "Format your response as a numbered list, one question per line."
            )

        # Fill template
        prompt_filled = prompt_text.replace("{{request}}", str(shared.get("request", ""))).replace(
            "{{initial_findings}}", initial_findings
        )

        # Use fast model when available per upstream behavior
        model_name = None
        try:
            model_name = shared.get("models", {}).get("fast")
        except Exception:
            model_name = None

        # Call LLM and parse a numbered list into questions
        if llm_client:
            raw = ""
            try:
                # Support multiple return shapes from various llm_client wrappers
                gen_res = llm_client.generate(prompt_filled, model=model_name)
                if isinstance(gen_res, tuple):
                    raw = gen_res[0]
                elif isinstance(gen_res, dict):
                    raw = gen_res.get("text") or gen_res.get("content") or ""
                else:
                    raw = gen_res
            except Exception as e:
                logger.debug("LLM clarifier generate failed: %s", e)
                raw = ""

            if raw:
                # raw may be a single string with numbered lines
                try:
                    # If JSON array returned, prefer that
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and parsed:
                        return [str(q).strip() for q in parsed][:4]
                except Exception:
                    pass

                # Split into lines, strip numbering
                qs_ls = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # remove leading numbering like '1.' or '1)'
                    cleaned = line
                    if cleaned.lstrip().startswith(("1.", "1)")):
                        cleaned = cleaned.split(".", 1)[-1].strip() if "." in cleaned else cleaned
                    # remove leading digits+punct
                    cleaned = cleaned.lstrip("0123456789. )-")
                    if cleaned:
                        qs_ls.append(cleaned.strip())
                    if len(qs_ls) >= 4:
                        break
                if qs_ls:
                    return qs_ls

        return default_q_ls

    def exec(self, questions):
        """Simulate presenting questions to the user and collect clarifications.

        Args:
            questions : The questions returned by :meth:`prep`.

        Returns:
            A simple clarification string (in production this would be user-provided answers).

        """
        logger.info("Presenting clarifying questions to user...")
        # If a pre-written clarifying QA file was provided, return its raw contents
        # (upstream parity)
        # shared['clarifying_qa'] is expected to be a filepath to a file containing inline answers.
        # Read and return as-is so downstream nodes (reporter) can include it verbatim.
        # Note: keep existing LLM auto-answer behavior as a non-default fallback only if
        # an explicit flag is set in shared (e.g., 'auto_answer_clarifier').
        return_text = None
        shared = getattr(self, "shared", {}) or {}
        clarifying_file = shared.get("clarifying_qa")
        if clarifying_file:
            try:
                if os.path.isfile(clarifying_file):
                    with open(clarifying_file, "r", encoding="utf-8") as f:
                        return_text = f.read()
                else:
                    # try relative path from cwd
                    rel = os.path.join(os.getcwd(), clarifying_file)
                    if os.path.isfile(rel):
                        with open(rel, "r", encoding="utf-8") as f:
                            return_text = f.read()
            except Exception as e:
                logger.warning("Failed to read clarifying_qa file %s: %s", clarifying_file, e)

        if return_text is not None:
            return return_text

        # Interactive editor branch: open editor for user to answer
        try:
            editor_file = shared.get("editor_file") if shared else None
            editor_content = "Please review the following questions and provide inline answers:\n\n"
            for q in questions:
                editor_content += q + "\n\n"

            edited = edit_text(editor_content, editor_file)
            return edited
        except Exception:
            # Last-resort: if automation requested, optionally auto-answer via LLM
            if shared.get("auto_answer_clarifier") and llm_client:
                answers = []
                for q in questions:
                    try:
                        ans_raw, _ = llm_client.generate(f"Q: {q}\nA:")
                        answers.append({"question": q, "answer": ans_raw})
                    except Exception:
                        answers.append({"question": q, "answer": "No clarification provided."})
                # Convert to a readable inline string
                lines = []
                for a in answers:
                    lines.append(f"Q: {a['question']}\nA: {a['answer']}\n")
                return "\n".join(lines)
            # If all else fails, return an empty string
            return ""

    def post(self, shared, prep_res, exec_res):
        """Store clarifications into the shared flow state.

        Args:
            shared : Shared flow state to update.
            prep_res : The questions that were asked.
            exec_res : The clarifications collected from the user.

        Returns:
            None

        """
        # Upstream parity: store the raw exec_res (string) as shared['clarifications']
        # so downstream report templates can include it verbatim.
        if isinstance(exec_res, str):
            shared["clarifications"] = exec_res
        else:
            # If exec_res is structured (list/dict), serialize to a readable string
            try:
                shared["clarifications"] = json.dumps(exec_res, indent=2)
            except Exception:
                shared["clarifications"] = str(exec_res)

        logger.info("Clarifications stored.")
        return None
