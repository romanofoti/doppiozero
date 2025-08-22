"""
fetch_github_conversation.py
Module for fetching and exporting GitHub issue, pull request, or discussion data as structured JSON.
"""
from typing import Optional, Dict, Any
import os
import json
import datetime


def fetch_github_conversation(conversation_url: str, cache_path: Optional[str] = None, updated_at: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch and export GitHub issue, pull request, or discussion data as structured JSON.

    Args:
        conversation_url (str): URL of the GitHub conversation.
        cache_path (Optional[str]): Directory for caching data (default: None).
        updated_at (Optional[str]): Only fetch if remote conversation is newer than this timestamp.

    Returns:
        Dict[str, Any]: Conversation data as a JSON object.
    """
    # Step 1: Simulate fetching GitHub conversation data (replace with real API call)
    conversation_data = {
        "url": conversation_url,
        "title": "Sample Issue Title",
        "author": "octocat",
        "state": "open",
        "created_at": "2025-08-01T12:00:00Z",
        "updated_at": "2025-08-20T15:00:00Z",
        "comments": [
            {"author": "octocat", "body": "First comment."},
            {"author": "hubot", "body": "Second comment."}
        ]
    }

    # Step 2: Handle updated_at logic
    if updated_at:
        try:
            updated_at_dt = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            convo_updated_dt = datetime.datetime.fromisoformat(conversation_data["updated_at"].replace('Z', '+00:00'))
            if convo_updated_dt <= updated_at_dt:
                print("Conversation not updated since provided timestamp.")
                return {}
        except Exception as e:
            print(f"Error parsing updated_at: {e}")

    # Step 3: Optionally cache the data
    if cache_path:
        os.makedirs(cache_path, exist_ok=True)
        safe_url = conversation_url.replace('/', '_').replace(':', '_')
        cache_file = os.path.join(cache_path, f"conversation_{safe_url}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f)
        except Exception as e:
            print(f"Error writing cache file: {e}")

    return conversation_data
