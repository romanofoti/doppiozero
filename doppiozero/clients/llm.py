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
import urllib

from typing import Dict, List, Optional

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
    api_base : Optional[str]
        Base URL for the API. Falls back to OPENAI_API_BASE environment variable.
    api_url : Optional[str]
        Specific API URL for the request. Falls back to OPENAI_URL environment variable.
    verbose : bool
        Whether to print verbose logging information.

    Attributes
    ----------
    api_key : Optional[str]
        The API key used for requests.
    api_base : str
        The API base URL used for requests.
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
        """Create an LLM client using optional API credentials and base URL.

        Args:
            api_key : Optional API key; falls back to OPENAI_API_KEY env var.
            api_base : Optional API base URL; falls back to OPENAI_API_BASE env var.
            api_url : Optional API URL; falls back to OPENAI_URL env var.

        Returns:
            None

        """
        self.api_key = api_key or os.environ.get("AZURE_OAI_O4_MINI_KEY")
        self.api_url = api_url or os.environ.get("OPENAI_URL")
        self.verbose = verbose

    def _process_raw_output(self, raw_output) -> Dict[str, Any]:
        """Parse the LLM output and extract only the 'determination' dictionary.

        Args:
            raw_output (str): The raw output string from the LLM.

        Returns:
            dict: A dictionary containing the 'determination' fields if present.

        Note:
            - If the output is a valid JSON object with a 'determination' key, it returns that.
            - If the output is malformed, it returns an empty dict.

        """

        yaml_str = raw_output.split("```yaml")[-1].split("```")[0].strip()
        response_dc = yaml.safe_load(yaml_str)
        return response_dc if isinstance(response_dc, dict) else {}

    def _call_openai_api(self, path: str, payload: dict) -> dict:
        """Perform an HTTP POST to the OpenAI-compatible REST endpoint.

        Args:
            path : The API path (e.g. '/v1/chat/completions').
            payload : The JSON-serializable payload to send.

        Returns:
            The parsed JSON response as a dictionary.

        """
        url = self.api_url
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        req = urllib.request.Request(url, data=data, headers=headers)

        response_dc = {}
        raw_output = ""

        logger.info("-------------------------------------")
        logger.info("Submitting the request to the LLM...")
        logger.info("-------------------------------------")

        try:
            response = urllib.request.urlopen(req)
            result = response.read()
            result_dc = json.loads(result.decode("utf8", "ignore"))
            raw_output = result_dc["choices"][0]["message"]["content"]
            logger.info("-------------------------------------")
            logger.info(raw_output)
            finish_reason = result_dc["choices"][0]["finish_reason"]
            metadata_dc = {
                "usage": result_dc.get("usage"),
                "finish_reason": finish_reason,
            }
            response_dc = self.process_raw_output(raw_output)
            response_dc["metadata_dc"] = metadata_dc
        except urllib.error.HTTPError as error:
            logger.info("-------------------------------------")
            logger.error("The urllib request failed with status code: " + str(error.code))
            logger.error(error.info())
            logger.error(error.read().decode("utf8", "ignore"))
            logger.info("-------------------------------------")
        except Exception as error:
            logger.info("-------------------------------------")
            logger.error("The attempt failed with the following error: " + str(error))
            logger.error(error)
            logger.info("-------------------------------------")

        logger.info("**********************************")
        logger.info("Returning the following output:")
        logger.info(json.dumps(response_dc, indent=2))
        logger.info("**********************************")

        return response_dc, raw_output

    def generate(self, prompt: str, model: Optional[str] = None, max_tokens: int = 1024) -> str:
        """Return a string generated by the configured LLM or a deterministic stub.

        Args:
            prompt : The prompt text to send to the LLM.
            model : Optional model name to override the default.
            max_tokens : Maximum tokens to request from the API.

        Returns:
            A generated text string from the LLM or a simulated summary on fallback.

        """
        if self.api_key:
            payload_dc = {
                "model": os.environ.get("MODEL"),
                "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": int(os.environ.get("MAX_TOKENS", 1024)),
            }
            try:
                response_dc, raw_output = self._call_openai_api(payload_dc)
                if response_dc:
                    return response_dc
                return ""
            except Exception as e:
                raise RuntimeError(f"LLM request failed: {e}")
        # Fallback stub
        excerpt = prompt[:400]
        return f"[SIMULATED SUMMARY]\n\n{excerpt}\n..."

    def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """Return an embedding vector (list of floats) for the given text.

        Args:
            text : The input text to embed.
            model : Optional model name to override the default embedding model.

        Returns:
            A list of floats representing the embedding vector.

        """
        if self.api_key:
            model_name = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
            payload_dc = {"model": model_name, "input": text}
            try:
                resp = self._call_openai_api("/v1/embeddings", payload_dc)
                data_ls = resp.get("data") or []
                if data_ls:
                    return data_ls[0].get("embedding", [])
                return []
            except Exception as e:
                raise RuntimeError(f"Embeddings request failed: {e}")
        # Fallback deterministic pseudo-embedding
        v_ls = [0.0] * 128
        h = 0
        for ch in text:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        for i in range(len(v_ls)):
            v_ls[i] = ((h >> (i % 32)) & 0xFF) / 255.0
        return v_ls


# Backward-compat convenience: a default client instance can be used by callers
# that prefer not to instantiate explicitly. We will update callers to use the
# class directly, but keep this here for optional compatibility.
llm_client = LLMClient()

# Note: `llm_client` is the canonical default client instance.
