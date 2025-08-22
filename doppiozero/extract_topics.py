"""
extract_topics.py
Module for extracting key thematic topics from a GitHub conversation using a prompt file.
"""

from typing import List, Optional
import os
import json


def extract_topics(conversation_url: str, topics_prompt_path: str, cache_path: Optional[str] = None, max_topics: Optional[int] = None) -> List[str]:
    """
    Extract key thematic topics from a GitHub conversation using a prompt file.

    Args:
        conversation_url (str): URL of the GitHub conversation (issue, PR, or discussion).
        topics_prompt_path (str): Path to the prompt file for topic extraction.
        cache_path (Optional[str]): Directory for caching topics (default: None).
        max_topics (Optional[int]): Maximum number of topics to extract (default: None).

    Returns:
        List[str]: Extracted topics as a list of strings.
    """
    # Step 1: Simulate fetching conversation text (replace with real fetch in production)
    conversation_text = f"Conversation from {conversation_url}..."

    # Step 2: Read the prompt file
    try:
        with open(topics_prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        return []

    # Step 3: Simulate LLM topic extraction (replace with real LLM call)
    # For demonstration, extract up to max_topics dummy topics
    base_topics = ["performance", "authentication", "database", "caching", "bug-fix", "security", "documentation"]
    if max_topics is not None:
        topics = base_topics[:max_topics]
    else:
        topics = base_topics

    # Step 4: Optionally cache the topics
    if cache_path:
        os.makedirs(cache_path, exist_ok=True)
        # Use a simple filename based on URL
        safe_url = conversation_url.replace('/', '_').replace(':', '_')
        cache_file = os.path.join(cache_path, f"topics_{safe_url}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(topics, f)
        except Exception as e:
            print(f"Error writing cache file: {e}")

    return topics
