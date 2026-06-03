## Chat style / response policy (read first)

- When the user asks a direct question (i.e., a request for information or a short confirmation) respond with the concise answer only. Do not include any leading or framing sentence such as "I'll answer", "I will now explain", "Here's what I'll do next", or any other meta-commentary. Don't include checklists. Don't provide next steps. Just answer as if you were a chat. Limit the answer to <=200 words unless the user explicitly asks for more by saying "Please elaborate your answer". If a clarifying question is essential, ask it in one sentence only and without preamble.
- If I ask you to carry out a task, only provide the plan checklist, a live explanation of your actions as you carry them out, a concise summary of results and a list of suggested next steps. Only resort to your default operating style if I explicitly request it by saying "Please elaborate" at the end of the message or as a follow up message.

Additional guidelines:
- When changing files, list files changed (path + one-line purpose).
- Include a “How I validated” line with quick results (build/test/pass/fail) if applicable.
- Ask a single clarifying question if instructions are ambiguous.
- When editing files, run quick validation: `poetry run pytest` (if available) or `poetry run flake8 .` and report PASS/FAIL. If tests cannot be run, state why (missing venv, env vars, etc).

## Quick context

- `doppiozero` is the **agentic core framework** for Romano's personal projects. It provides reusable primitives — node-graph orchestration, LLM/GitHub clients, shared utilities — that downstream personal projects depend on to build their own agents.
- It is a library, not an application. There is no flagship agent in this repo. `SupervisorAgent` (`doppiozero/agents/supervisor.py`) exists only as a small reference example showing how to compose nodes; it is not the purpose of the package.
- The orchestration substrate is PocketFlow (`doppiozero/pocketflow/pocketflow.py`), inspired by the patterns in `jonmagic/scripts` (https://github.com/jonmagic/scripts). The LLM surface is `doppiozero.clients.llm.LLMClient`.
- Do not change `pocketflow/pocketflow.py` — its `Node`/`Flow` contract is depended on by every consumer. Fix nodes, not the orchestrator.

## High-level architecture

- **Orchestration** — `doppiozero/pocketflow/pocketflow.py` defines `Node`, `Flow`, and async variants. Nodes implement `prep(shared) -> prep_res`, `exec(prep_res) -> exec_res`, and `post(shared, prep_res, exec_res) -> action_token`. The `Flow` uses the action token (a small hashable like a string or `None`) to pick successors.
- **Clients** — `doppiozero/clients/llm.py` (generation + embeddings) and `doppiozero/clients/github.py` (PyGithub adapter). These are the canonical I/O surfaces for downstream agents.
- **Utilities** — `doppiozero/utils/utils.py` exposes `get_logger` and shared helpers. Domain-specific helpers (`contents.py`, `meetings.py`) sit at the top of the package.
- **Reference example** — `doppiozero/agents/supervisor.py` plus `doppiozero/nodes/supervisor/*` shows a Decider/Searcher/Answerer/Supervisor loop. Treat it as a usage example, not as a load-bearing part of the framework. Do not expand it speculatively.

## Important developer rules & conventions

- Do NOT edit `doppiozero/pocketflow/pocketflow.py`. The Flow semantics and routing contract must remain stable across consumers. Fix nodes rather than the orchestrator if you encounter routing/type issues.
- Node return values matter: nodes should place structured outputs into the shared dict and return a small, hashable action token (string or `None`). Returning dicts or lists as the action causes `TypeError: "unhashable type"` during orchestration.
- Naming conventions: lists use the `_ls` suffix and dicts use the `_dc` suffix in variable names. The base name before the suffix should be singular (`item_ls`, not `items_ls`).
- LLM return shapes: `LLMClient.generate` may return a tuple `(structured_dc, raw_resp)`, a dict, or a string depending on configuration. Caller code should defensively inspect the type before using the content.
- Library discipline: this is a framework. Do not add application-level concerns (CLIs, fixtures, project-specific prompts) here. Those belong in downstream personal projects that depend on `doppiozero`.


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
- Headless notebook execution (occasional, for example when validating the supervisor example): register the poetry venv as a Jupyter kernel and execute with nbconvert. Example:

  poetry run python -m nbconvert --to notebook --execute supervisor_agent.ipynb \
    --ExecutePreprocessor.timeout=600 \
    --ExecutePreprocessor.kernel_name=doppiozero-poetry \
    --output executed_supervisor_agent.ipynb

## Tests and debugging

- Unit tests live in `tests/unit/` (run with `poetry run pytest -q`).
- Logging: modules use `doppiozero.utils.utils.get_logger`. When debugging consumer agents, pass a `verbose` flag through the shared dict so nodes can emit detail (the supervisor example follows this pattern).

## Files worth reading first

- `doppiozero/pocketflow/pocketflow.py` — `Flow` & `Node` primitives (read carefully — this is the contract every consumer relies on)
- `doppiozero/clients/llm.py` — LLM client behavior and environment variables
- `doppiozero/clients/github.py` — GitHub adapter
- `doppiozero/agents/supervisor.py` and `doppiozero/nodes/supervisor/*` — small reference example of how to wire a flow

## What not to change

- Do not modify `doppiozero/pocketflow/pocketflow.py` to fix node routing issues. Fix nodes so they obey the routing contract instead.
- Do not bolt application-specific logic onto the framework. New agents and project glue belong in the consuming repositories, not here.
