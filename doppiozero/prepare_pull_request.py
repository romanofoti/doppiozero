"""
prepare_pull_request.py
Module for generating a pull request title and body based on commits and diffs using an LLM and a prompt file.
"""

from typing import Optional, Tuple


def prepare_pull_request(
    base_branch: str, pr_body_prompt_path: str, llm_model: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generate a pull request title and body based on commits and diffs using an LLM and a prompt file.

    Args:
        base_branch (str): Name of the base branch to compare against.
        pr_body_prompt_path (str): Path to prompt file for generating PR body.
        llm_model (Optional[str]): Specific LLM model to use (default: None).

    Returns:
        Tuple[str, str]: Generated PR title and body.
    """
    # Step 1: Read the PR body prompt
    try:
        with open(pr_body_prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        print(f"Error reading PR body prompt: {e}")
        return "", ""

    # Step 2: Simulate LLM PR title/body generation
    model_str = llm_model if llm_model else "default-llm"
    pr_title = f"[{model_str}] PR for {base_branch}: {prompt[:40]}..."
    pr_body = f"[{model_str}] PR body: {prompt[:120]}..."
    return pr_title, pr_body
