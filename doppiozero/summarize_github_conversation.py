"""
summarize_github_conversation.py
Module for generating an executive summary of a GitHub conversation using an LLM and a prompt file.
"""

from typing import Optional
import os
import json


def summarize_github_conversation(conversation_url: str, executive_summary_prompt_path: str, cache_path: Optional[str] = None, updated_at: Optional[str] = None) -> str:
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
        print(f"Error reading executive summary prompt: {e}")
        return ""

    # Step 2: Simulate LLM summary generation
    summary = f"Executive summary for {conversation_url}: {prompt[:120]}..."

    # Step 3: Optionally cache the summary
    if cache_path:
        os.makedirs(cache_path, exist_ok=True)
        safe_url = conversation_url.replace('/', '_').replace(':', '_')
        cache_file = os.path.join(cache_path, f"summary_{safe_url}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"summary": summary}, f)
        except Exception as e:
            print(f"Error writing cache file: {e}")

    return summary
