from ..pocketflow.pocketflow import Node
from ..utils.utils import get_logger
from ..clients.llm import llm_client
from typing import Any
import json

logger = get_logger(__name__)


class PlannerNode(Node):
    """Node responsible for creating search plans from a request.

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
    The planner creates a set of search queries (semantic, keyword, etc.) and
    writes the resulting plans into shared state under ``next_search_plans``.

    """

    def prep(self, shared):
        """Build initial query templates based on the user's request.

        Args:
            shared : Shared flow state. Expected to include ``request``.

        Returns:
            A dictionary with query templates for different search tools.

        """
        logger.info("=== PLANNING PHASE ===")
        # Preserve shared for exec() to access runtime options
        self.shared = shared

        depth = int(shared.get("current_depth", 0))
        max_depth = int(shared.get("max_depth", 2))
        logger.info("=== PLANNING PHASE (Iteration %d/%d) ===", depth + 1, max_depth)

        # Priority 1: If verification produced unsupported claims, focus search
        unsupported = shared.get("unsupported_claims") or []
        if unsupported:
            logger.info(
                "Focusing search on gathering evidence for %d unsupported claims",
                len(unsupported),
            )
            # Format unsupported claims for LLM processing
            unsupported_claim_ls = []
            for i, c in enumerate(unsupported or []):
                unsupported_claim_ls.append(f"{i+1}. {c}")
            unsupported_claims_text = "\n".join(unsupported_claim_ls)

            findings_summary = "\n\n".join(shared.get("memory", {}).get("notes", []) or [])
            previous_queries = ", ".join(shared.get("memory", {}).get("search_queries", []) or [])

            # Try an upstream-style prompt file, else use a compact inline prompt
            cwd = None
            try:
                import os

                cwd = os.getcwd()
            except Exception:
                cwd = None

            prompt_text = None
            if cwd:
                p = os.path.join(cwd, "prompts", "refine", "unsupported_claims_research.md")
                if os.path.isfile(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            prompt_text = f.read()
                    except Exception:
                        prompt_text = None

            if not prompt_text:
                prompt_text = (
                    "You are an expert researcher focusing on verifying unsupported claims.\n\n"
                    "Given the request, clarifications, previous findings, and the list of "
                    "unsupported claims, generate a JSON object with a 'query' field "
                    "(natural-language).\n\n"
                    "Include optional 'created_after', 'created_before', and 'order_by' fields "
                    "to narrow search.\n\nReturn the raw JSON only.\n\n"
                    "Request: {{request}}\nClarifications: {{clarifications}}\n"
                    "Unsupported: {{unsupported}}\nFindings: {{findings_summary}}\n"
                    "Previous queries: {{previous_queries}}"
                )

            filled = (
                prompt_text.replace("{{request}}", str(shared.get("request", "")))
                .replace("{{clarifications}}", str(shared.get("clarifications", "")))
                .replace("{{unsupported}}", unsupported_claims_text)
                .replace("{{findings_summary}}", findings_summary)
                .replace("{{previous_queries}}", previous_queries)
            )

            try:
                model = shared.get("models", {}).get("fast")
                resp = llm_client.generate(filled, model=model) if llm_client else ""
            except Exception as e:
                logger.debug("Planner LLM call failed: %s", e)
                resp = ""

            raw = self._normalize_llm_text(resp)
            # Try JSON parse
            try:
                parsed = json.loads(raw)
                logger.info("Generated claim verification search plan: %s", parsed)
                return parsed
            except Exception:
                # Fallback: return raw string as a simple query
                logger.info("Generated raw search query: %s", raw)
                return {"query": raw}

        # Priority 2: Check iteration depth limits
        if depth >= max_depth:
            logger.info("Maximum depth reached, moving to final report")
            return None

        # Otherwise fall back to simple generation for configured search modes
        return {
            "semantic": {"query": shared.get("request")},
            "keyword": {"query": shared.get("request")},
        }

    def exec(self, plan):
        """Transform query templates into executable search plans.

        Args:
            plan : The query templates produced by :meth:`prep`.

        Returns:
            A list of search plan dicts each containing a ``tool`` and ``query``.

        """
        logger.info("Transforming queries into search plans...")
        # If the planner indicated no further work, return None to signal final
        if plan is None:
            return None

        # Store current query for downstream inspection
        self.shared["current_query"] = plan

        search_modes = self.shared.get("search_modes", ["semantic", "keyword"])
        search_plan_ls = []

        for mode in search_modes:
            if mode == "semantic":
                # Accept structured or string formats
                if isinstance(plan, dict) and plan.get("semantic"):
                    semantic = plan.get("semantic")
                    if isinstance(semantic, dict):
                        q = semantic.get("query") or ""
                    else:
                        q = str(semantic)
                elif isinstance(plan, dict) and plan.get("query"):
                    q = plan.get("query")
                else:
                    q = str(plan)

                search_plan_dc = {"tool": "semantic", "query": q}
                # propagate optional filters
                if isinstance(plan, dict) and isinstance(plan.get("semantic"), dict):
                    s = plan.get("semantic")
                    for key in ("created_after", "created_before", "order_by"):
                        if key in s:
                            search_plan_dc[key] = s[key]
                elif isinstance(plan, dict):
                    for key in ("created_after", "created_before", "order_by"):
                        if key in plan:
                            search_plan_dc[key] = plan[key]

                search_plan_ls.append(search_plan_dc)

            elif mode == "keyword":
                if isinstance(plan, dict) and plan.get("keyword"):
                    q = plan.get("keyword")
                elif isinstance(plan, dict) and plan.get("query"):
                    q = plan.get("query")
                else:
                    q = str(plan)
                search_plan_ls.append({"tool": "keyword", "query": q})

        return search_plan_ls

    # --- helpers ---
    def _normalize_llm_text(self, resp: Any) -> str:
        """Normalize different llm_client.generate return shapes into a string."""
        if resp is None:
            return ""
        if isinstance(resp, (tuple, list)):
            first = resp[0] if len(resp) > 0 else resp
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                # try common keys
                for k in ("text", "content", "output", "result"):
                    if k in first:
                        return str(first[k])
                try:
                    return json.dumps(first)
                except Exception:
                    return str(first)
        if isinstance(resp, dict):
            if "choices" in resp and isinstance(resp["choices"], list):
                try:
                    return resp["choices"][0]["message"]["content"]
                except Exception:
                    pass
            return json.dumps(resp)
        return str(resp)

    def post(self, shared, prep_res, exec_res):
        """Store generated search plans into the shared flow state.

        Args:
            shared : Shared flow state to update.
            prep_res : The templates returned by :meth:`prep`.
            exec_res : The list of search plans returned by :meth:`exec`.

        Returns:
            None

        """
        # If prep_res is None we reached max depth and should route to final
        if prep_res is None:
            return "final"

        shared["next_search_plans"] = exec_res
        logger.info("\u2713 Planning complete, generated %d search plans", len(exec_res or []))
        logger.debug("Moving to retrieval phase...")
        return None
