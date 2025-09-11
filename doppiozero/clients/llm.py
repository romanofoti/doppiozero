"""Lightweight LLM client wrapper.

Provides two functions used by the agent:
- generate(prompt, model=None): returns a string completion
- embed(text, model=None): returns a list[float]

If OPENAI_API_KEY is present in the environment, the client will call the
OpenAI REST API. Otherwise it falls back to deterministic local stubs so the
code is testable without network access.
"""

import json
import os
import yaml

from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from ..utils.utils import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Lightweight LLM client wrapper providing text generation and embeddings.

    Parameters
    ----------
    api_key : Optional[str]
        API key for the OpenAI-compatible endpoint. Falls back to the
        OPENAI_API_KEY environment variable when omitted.
    api_url : Optional[str]
        Specific API URL for the request. Falls back to OPENAI_URL environment variable.
    verbose : bool
        Whether to print verbose logging information.

    Attributes
    ----------
    api_key : Optional[str]
        The API key used for requests.
    api_url : str
        The specific API URL used for requests.
    verbose : bool
        Whether to print verbose logging information.

    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_url: Optional[str] = None,
        verbose: bool = False,
    ):
        """Create an LLM client using optional API credentials.

        This constructor is intentionally LAZY: it does not raise if credentials
        are absent. Environment variables are (re)read on the first call to
        :meth:`generate` or :meth:`embed` so notebooks can call ``load_dotenv``
        after importing the module without breaking the singleton import pattern.

        Checked environment variable order for the API key:
        1. Explicit ``api_key`` argument
        2. ``GPT_5_MINI_KEY`` (project specific)
        3. ``OPENAI_API_KEY`` (generic)
        4. ``AZURE_OAI_4O_KEY`` (alternate naming)

        The API URL is taken from the explicit ``api_url`` argument or the
        ``OPENAI_URL`` environment variable. If still absent at call time a
        deterministic stub is used.
        """
        self.api_key = (
            api_key
            or os.environ.get("GPT_5_MINI_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("AZURE_OAI_4O_KEY")
        )
        self.api_url = api_url or os.environ.get("OPENAI_URL")
        self.verbose = verbose

    # --- internal helpers ---
    def _refresh_env_if_needed(self):
        """Refresh environment-derived credentials if they are currently missing.

        Called at the start of each public operation to enable late loading of
        environment variables (e.g. after ``load_dotenv()`` in a notebook).
        """
        if not self.api_key:
            self.api_key = (
                os.environ.get("GPT_5_MINI_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("AZURE_OAI_4O_KEY")
            )
            if self.api_key:
                logger.info("[LLM] Acquired API key ending with %s", self.api_key[-4:])
        if not self.api_url:
            self.api_url = os.environ.get("OPENAI_URL")
            if self.api_url:
                logger.info("[LLM] Using API URL: %s", self.api_url)

    def _process_raw_output(self, result_dc) -> Dict[str, Any]:
        """Normalize raw OpenAI / Azure response content into a dict.

        Parsing strategy (defensive to avoid noisy errors on plain text):
        1. Extract message content.
        2. If fenced YAML block detected (```yaml), parse just that block.
        3. Else if content looks like JSON (starts with { or [), attempt JSON parse.
        4. Else if colon-heavy structure suggests YAML (simple heuristic), attempt YAML parse.
        5. On any parse failure, return a fallback dict with the raw text.

        Always returns a dictionary so downstream code has a consistent shape.
        """
        try:
            raw_output = result_dc.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            raw_output = ""

        if not raw_output:
            return {"fallback": "empty_response"}

        content = raw_output.strip()
        lower_content = content.lower()

        # Case 1: fenced yaml
        if "```yaml" in lower_content:
            try:
                yaml_block = raw_output.split("```yaml", 1)[1].split("```", 1)[0].strip()
                parsed = yaml.safe_load(yaml_block)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"items": parsed}
            except Exception:
                logger.warning("Failed to parse YAML block!")
                logger.warning(f"Content output: {content}")
                return {"fallback": content}

        # Case 2: looks like JSON
        if content.startswith("{") or content.startswith("["):
            try:
                parsed_json = json.loads(content)
                if isinstance(parsed_json, dict):
                    return parsed_json
                logger.warning("Failed to parse JSON response as a dictionary!")
                logger.warning(f"Parsed JSON items: {parsed_json}")
                return {"items": parsed_json}
            except Exception:
                pass

        # Case 3: heuristic YAML (multiple lines with ': ')
        colon_lines = 0
        total_lines = 0
        for ln in content.splitlines()[:20]:  # inspect only first 20 lines
            total_lines += 1
            if ":" in ln:
                colon_lines += 1
        if total_lines > 0 and colon_lines / total_lines > 0.6:
            try:
                parsed_yaml = yaml.safe_load(content)
                if isinstance(parsed_yaml, dict):
                    return parsed_yaml
                if isinstance(parsed_yaml, list):
                    return {"items": parsed_yaml}
            except Exception:
                pass

        # Fallback: treat as plain text (enumerated list, etc.)
        return {"fallback": content}

    def _call_openai_api(
        self,
        prompt: str,
        request_type: str = "chat",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Call the OpenAI-compatible API for either chat completions or embeddings.

        Args:
            prompt: The input text (prompt for chat or input for embeddings).
            request_type: Either 'chat' (default) or 'embed'.
            model: Optional model override.
            max_tokens: Optional max tokens for chat responses.

        Returns:
            The raw response dictionary from the client.
        """

        # Caller ensures _refresh_env_if_needed has run. If still missing
        # credentials we operate in stub mode and never invoke network calls.
        if not self.api_key or not self.api_url:
            raise RuntimeError("LLM client not configured (missing api key or url)")

        client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.api_url,
            api_key=self.api_key,
        )

        if self.verbose:
            logger.info("-------------------------------------")
            logger.info(f"Submitting the request to the LLM ({request_type})...")
            logger.info("-------------------------------------")

        if request_type == "embed":
            model_name = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
            resp = client.embeddings.create(model=model_name, input=prompt).dict()
            return resp

        # default: chat/generation. Use per-call override when provided, else env.
        effective_max = (
            max_tokens if max_tokens is not None else int(os.environ.get("MAX_TOKENS", 1024))
        )
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=effective_max,
            model=model or os.environ.get("MODEL", "gpt-5-mini"),
        ).dict()

        return resp

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Return a string generated by the configured LLM or a deterministic stub.

        Args:
            prompt : The prompt text to send to the LLM.
            model : Optional model name to override the default.

        Note:
            If ``max_tokens`` is provided it overrides the environment MAX_TOKENS for this call.

        Returns:
            A tuple containing the result and response dictionaries:
                response_dc : The raw response from the LLM API
                result_dc : The processed result from the LLM

        """
        # Ensure we have the latest env vars if they were loaded after import
        self._refresh_env_if_needed()
        result_dc: Dict[str, Any] = {}
        response_dc: Dict[str, Any] = {}
        try:
            response_dc = self._call_openai_api(
                prompt, request_type="chat", model=model, max_tokens=max_tokens
            )
            result_dc = self._process_raw_output(response_dc)
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            # Fall back to deterministic stub output rather than raising
            result_dc = {"fallback": "llm_error"}
            response_dc = {"error": str(e)}

        if self.verbose:
            logger.info("**********************************")
            logger.info("Returning the following output:")
            if result_dc:
                logger.info(json.dumps(result_dc, indent=2))
            else:
                result_dc = {"fallback": "Dummy output"}
                logger.info("No valid output received.")
            logger.info("**********************************")

        return result_dc, response_dc

    def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """Return an embedding vector (list of floats) for the given text.

        Args:
            text : The input text to embed.
            model : Optional model name to override the default embedding model.

        Returns:
            A list of floats representing the embedding vector.

        """
        self._refresh_env_if_needed()
        model_name = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        try:
            if self.verbose:
                logger.info("[EMBED] Requesting embedding using model %s", model_name)
            response_dc = self._call_openai_api(text, request_type="embed", model=model_name)
            data_ls = response_dc.get("data") or []
            embedding = data_ls[0].get("embedding", []) if data_ls else []
            if self.verbose:
                logger.info("[EMBED] Received embedding (len=%s)", len(embedding))
            return embedding
        except Exception:
            raise RuntimeError("Embeddings request failed!")


# Backward-compat convenience: a default client instance can be used by callers
# that prefer not to instantiate explicitly. We will update callers to use the
# class directly, but keep this here for optional compatibility.
llm_client = LLMClient()

# Note: `llm_client` is the canonical default client instance.
