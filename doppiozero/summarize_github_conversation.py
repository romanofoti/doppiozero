"""
summarize_github_conversation.py
Module for generating an executive summary of a GitHub conversation using an LLM and a prompt file.
"""

from typing import Optional
import os
import json
import logging

from .content_fetcher import content_fetcher
from .llm_client import llm_client
from .utils.utils import get_logger, write_json_safe
from .utils.scripts_common import safe_filename_for_url

logger = get_logger(__name__)


def summarize_github_conversation(
    conversation_url: str,
    executive_summary_prompt_path: str,
    cache_path: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> str:
    """
    Generate an executive summary of a GitHub conversation using an LLM and a prompt file.

    Args:
        conversation_url (str): URL of the GitHub conversation.
        executive_summary_prompt_path (str): Path to executive summary prompt file.
        cache_path (Optional[str]): Directory for caching summary (default: None).
        updated_at (Optional[str]): Only fetch if remote conversation is newer than this timestamp.

    Returns:
        str: Executive summary text.
    """
    # Step 1: Read the executive summary prompt
    try:
        with open(executive_summary_prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        logger.error(f"Error reading executive summary prompt: {e}")
        return ""

    # Step 2: Fetch conversation and construct LLM prompt
    convo_dc = content_fetcher.fetch_github_conversation(
        conversation_url, cache_path=cache_path, updated_at=updated_at
    )
    convo_text = json.dumps(convo_dc, indent=2)[:8000]
    full_prompt = prompt.replace("{{conversation}}", convo_text).replace(
        "{{url}}", conversation_url
    )

    # Step 3: Call LLM
    try:
        summary = llm_client.generate(full_prompt)
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        # Fallback stub
        summary = f"Executive summary for {conversation_url}: {prompt[:120]}..."

    # Step 3: Optionally cache the summary
    if cache_path:
        safe_url = safe_filename_for_url(conversation_url)
        cache_file = os.path.join(cache_path, f"summary_{safe_url}.json")
        try:
            write_json_safe(cache_file, {"summary": summary})
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")

    return summary
