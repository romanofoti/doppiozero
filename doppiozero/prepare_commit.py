"""
prepare_commit.py
Module for generating a semantic commit message for staged changes using an LLM and a prompt template.
"""

from typing import Optional


def prepare_commit(commit_message_prompt_path: str, llm_model: Optional[str] = None) -> str:
    """
    Generate a semantic commit message for staged changes using an LLM and a prompt template.

    Args:
        commit_message_prompt_path (str): Path to commit message prompt file.
        llm_model (Optional[str]): Specific LLM model to use (default: None).

    Returns:
        str: Generated commit message.
    """
    # Step 1: Read the commit message prompt
    try:
        with open(commit_message_prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        print(f"Error reading commit message prompt: {e}")
        return ""

    # Step 2: Simulate LLM commit message generation
    model_str = llm_model if llm_model else "default-llm"
    commit_message = f"[{model_str}] Semantic commit message: {prompt[:60]}..."
    return commit_message
