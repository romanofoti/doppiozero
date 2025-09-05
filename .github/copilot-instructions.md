## Chat style / response policy (read first)

- When the user asks a direct question (i.e., a request for information or a short confirmation) respond with the concise answer only. Do not include any leading or framing sentence such as "I'll answer", "I will now explain", "Here's what I'll do next", or any other meta-commentary. Don't include checklists. Don't provide next steps. Just answer as if you were a chat. Limit the answer to <=200 words unless the user explicitly asks for more by saying "Please elaborate your answer". If a clarifying question is essential, ask it in one sentence only and without preamble.
- If I ask you to carry out a task, only provide the plan checklist, a live explanation of your actions as you carry them out, a concise summary of results and a list of suggested next steps. Only resort to your default operating style if I explicitly request it by saying "Please elaborate" at the end of the message or as a follow up message.

Additional guidelines:
- When changing files, list files changed (path + one-line purpose).
- Include a “How I validated” line with quick results (build/test/pass/fail) if applicable.
- Ask a single clarifying question if instructions are ambiguous.
- When editing files, run quick validation: `poetry run pytest` (if available) or `poetry run flake8 .` and report PASS/FAIL. If tests cannot be run, state why (missing venv, env vars, etc).

## Quick context

- This repository implements a node-based research agent (`doppiozero.agents.gh_deep_search.GitHubAgent`) that builds a Flow of small nodes (prep/exec/post) defined in `doppiozero/nodes/` and orchestrated by the PocketFlow primitives in `doppiozero/pocketflow/pocketflow.py`.
- This work is a python-based port of the work done in `jonmagic/scripts` (source code here: https://github.com/jonmagic/scripts). Please refer to the original repository whenever in doubt about implementation details.
- The LLM surface is `doppiozero.clients.llm.LLMClient`.
- The agent expects nodes to place structured outputs in the shared runtime dict (`agent.shared`) and to return small, hashable route tokens (strings or None) for the Flow to choose the next node.
- Do not change the orchestration in `pocketflow/pocketflow.py` — modifying it breaks the node contract.

## High-level architecture

- PocketFlow orchestration: `doppiozero/pocketflow/pocketflow.py` defines `Node`, `Flow`, and async variants. Nodes implement `prep(shared) -> prep_res`, `exec(prep_res) -> exec_res`, and `post(shared, prep_res, exec_res) -> action_token` (often None). The `Flow` uses the node's return value (the action token) to select successors.
- GitHubAgent: `doppiozero/agents/gh_deep_search.py` composes nodes into a Flow. Key nodes: `InitialResearchNode`, `ClarifierNode`, `PlannerNode`, `RetrieverNode` (or `ParallelRetrieverNode`), `ContextCompacterNode`, `VerifierNode` (or `ParallelClaimVerifierNode`), `FinalReportNode`, `End`.
- LLM client: `doppiozero/clients/llm.py` is the canonical interface for generation (`generate`) and embeddings (`embed`).

## Important developer rules & conventions

- Do NOT edit `doppiozero/pocketflow/pocketflow.py`. The Flow semantics and routing contract must remain stable. Fix nodes rather than the orchestrator if you encounter routing/type issues.
- Node return values matter: nodes should place structured outputs into the shared dict (for example, `shared['final_report']`) and return a small, hashable action token (string or None). Returning dicts or lists as the action causes TypeError: "unhashable type" during orchestration.
- Naming conventions: lists use the `_ls` suffix and dicts use `_dc` in variable names (follow this in new code for consistency). The variable name before the suffix should be singular (e.g. `item_ls` is fine, `items_ls` is not fine).
- LLM return shapes: `LLMClient.generate` may return a tuple `(structured_dc, raw_resp)`, a dict, or a string depending on configuration. Node code defensively inspects the type (tuple/dict/str) before using the content
- Editor & interactive behavior: nodes that open an editor (e.g., `edit_text`) must detect non-TTY environments (notebooks/headless) and fall back to reading a clarifying answers file (`clarifying_answers.txt`) or returning empty strings. See `ClarifierNode` for the exact pattern.


### Annotations and docstrings conventions

All classes and methods should be annotated with their expected input and output types and should have docstrings explaining their behavior.

Example format for classes docstring:

```
class GitHubClient:
    """
    Light adapter over PyGithub providing normalized dictionaries for issues, PRs and discussions.

    Parameters
    ----------
    token : Optional[str]
        Optional GitHub API token. Falls back to the GITHUB_TOKEN environment
        variable when not provided.

    Attributes
    ----------
    gh : github.Github
        The underlying PyGithub client instance.
    """
```

Example format for methods docstring:

```
def fetch_issue(self, owner: str, repo: str, number: str) -> Dict[str, Any]:
    """Fetch an issue and return a normalized dictionary representation.

    Args:
        owner : Repository owner/login.
        repo : Repository name.
        number : Issue number (as string or int).

    Returns:
        A dictionary with normalized issue fields (url, title, body, comments, etc.).

    """
```

## Runtime & developer workflows

- Virtual environment & packaging: the project uses Poetry (see `pyproject.toml` and `poetry.lock`). Use `poetry run` to execute commands in the virtual environment.
- Headless notebook execution (used by CI or automation): register the poetry venv as a Jupyter kernel and execute with nbconvert. Example used by the repo:

  poetry run python -m nbconvert --to notebook --execute agent_test.ipynb \
    --ExecutePreprocessor.timeout=600 \
    --ExecutePreprocessor.kernel_name=doppiozero-poetry \
    --output executed_agent_test_real.ipynb

## Tests and debugging

- Unit tests live in `tests/` (run with `poetry run pytest`).
- Logging: modules use `doppiozero.utils.utils.get_logger`. When debugging, enable `verbose` in agent options to see node-level logging. Example:

  agent = GitHubAgent('query', {'verbose': True})

## Files worth reading first

- `doppiozero/pocketflow/pocketflow.py` — Flow & Node primitives (read carefully)
- `doppiozero/agents/gh_deep_search.py` — Agent wiring and expected node graph
- `doppiozero/clients/llm.py` — LLM client behavior and environment variables
- `doppiozero/contents.py` — content_manager/content_fetcher surface
- `doppiozero/nodes/clarifier.py` — clarifier patterns for non-tty and LLM defensiveness

## What not to change

- Do not modify `doppiozero/pocketflow/pocketflow.py` to fix node routing issues. Fix nodes so they obey the routing contract instead.
