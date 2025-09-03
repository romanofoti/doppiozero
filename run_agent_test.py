"""
Standalone runner for GitHubAgent (mocked content layer).
This avoids notebook execution and ensures clarifier reads a prewritten file instead of opening an editor.
"""

import sys
from pathlib import Path

# Ensure repo root on path
repo_root = Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import types
import json
from pprint import pprint

import doppiozero.contents as contents_mod
from doppiozero.agents.gh_deep_search import GitHubAgent

# --- Monkeypatch content layer ---
cm = getattr(contents_mod, "content_manager", None)
cf = getattr(contents_mod, "content_fetcher", None)


def fake_search(query, max_results=5):
    return [
        {"url": f"https://example.com/convo/{i}", "score": 1.0 - i * 0.1}
        for i in range(max_results)
    ]


def fake_vector_search(query, collection=None, top_k=5):
    return [
        {
            "url": f"https://example.com/convo/{i}",
            "summary": f"Summary of {query} #{i}",
            "score": 1.0 - i * 0.1,
        }
        for i in range(top_k)
    ]


def fake_fetch_github_conversation(url, cache_path=None):
    return {
        "url": url,
        "messages": [
            {"author": "alice", "text": "Initial issue description."},
            {"author": "bob", "text": "Follow-up discussion."},
        ],
    }


def fake_summarize(url, prompt_path=None, cache_path=None):
    return f"Compact summary for {url}"


def fake_vector_upsert(text, collection, metadata, model=None):
    return True


if cm is None:
    contents_mod.content_manager = types.SimpleNamespace()
    cm = contents_mod.content_manager
if cf is None:
    contents_mod.content_fetcher = types.SimpleNamespace()
    cf = contents_mod.content_fetcher

setattr(cm, "search", fake_search)
setattr(cm, "vector_search", fake_vector_search)
setattr(cm, "summarize", fake_summarize)
setattr(cm, "vector_upsert", fake_vector_upsert)
setattr(contents_mod, "content_manager", cm)
setattr(cf, "fetch_github_conversation", fake_fetch_github_conversation)
setattr(contents_mod, "content_fetcher", cf)

print("Patched content_manager and content_fetcher with deterministic mocks")

# write clarifying answers file
clarifying_path = repo_root / "clarifying_answers.txt"
with open(clarifying_path, "w", encoding="utf-8") as f:
    f.write(
        "Q: What is the main goal?\nA: Find recent authentication failure discussions across repos.\n\n"
    )
    f.write("Q: Are there specific repos to focus on?\nA: doppiozero and financial-planning.\n\n")

print("Wrote clarifying answers to", clarifying_path)

options = {
    "collection": None,
    "limit": 3,
    "max_depth": 1,
    "editor_file": None,
    "clarifying_qa": str(clarifying_path),
    "search_modes": ["semantic"],
    "cache_path": None,
    "models": {"fast": "default", "reasoning": "default", "embed": "default"},
    "parallel": False,
    "verbose": True,
}

agent = GitHubAgent("What are the recent discussions about authentication failures?", options)
result = agent.run()
print("\n=== AGENT RUN RESULT ===")
pprint(result)
print("\n=== SHARED STATE ===")
pprint(agent.shared)

# Save artifact
out_path = repo_root / "agent_test_output.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nSaved agent output to", out_path)
