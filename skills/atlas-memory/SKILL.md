---
name: atlas-memory
description: "Systematic Atlas session context preservation and restoration for personal projects. Two responsibilities: persist context at end-of-session, restore context at beginning-of-session. Sessions live in the active project repo, not in a shared store."
---

# Atlas Memory Management

Two responsibilities: persist session context when ending, restore it when starting. This is the personal-projects analog of `argus-memory`. Use it whenever Romano works on a multi-session, multi-day personal project (doppiozero, 00-fin/valuelens, future personal repos).

**Core principle:** Session notes are the destination for deliberation, brainstorming, drafts, and working state. Project roadmap docs (e.g., `docs/<slug>_roadmap.md`) are decisions only.

**Key difference from argus-memory:** sessions live **inside the active project repo**, not in a shared notes repo. There is no central index, no task-queue CLI, no semantic search infra. Keep it simple: filesystem + git.

## Active Repo Resolution

Before reading or writing session files, identify the active repo. Resolve in this order:

1. Explicit anchor in Romano's message ("resume valuelens", "continue doppiozero").
2. The repo that owns the file currently open in the editor.
3. The repo at the terminal cwd.

If ambiguous (multi-root workspace, no obvious anchor), ask Romano in one sentence which repo before doing anything else.

## Session Files

Location: `<active-repo>/sessions/YYYY-MM-DD/`

| File                | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `atlas-context.md`  | Priorities, decisions made, open questions, cross-references to roadmap doc.         |
| `work-state.md`     | Active branches, in-flight changes, files touched, what is next, blockers.           |
| `scratch.md`        | Ephemeral notes, debugging context, ideas (optional).                                |

Sessions are **committed to the repo** by Romano so they sync across machines and survive across conversations. Atlas writes them; Romano commits them (per operating principle 8: Atlas never commits).

### Frontmatter (required on `atlas-context.md` and `work-state.md`)

```yaml
---
project: <slug>            # roadmap doc slug, e.g. valuelens
date: YYYY-MM-DD
session_n: <int>           # nth session of the day, default 1
roadmap: docs/<slug>_roadmap.md
related_sessions: [YYYY-MM-DD, YYYY-MM-DD]
---
```

The frontmatter lets later sessions locate context without parsing prose.

## End-of-Session Protocol

1. **Identify active repo and project slug** (per Active Repo Resolution).
2. **Create the session folder** `sessions/YYYY-MM-DD/` if it does not exist.
3. **Write `atlas-context.md`** — capture:
   - One-line session summary.
   - Decisions taken (with reasoning, briefly).
   - Open questions for next session.
   - Roadmap doc deltas (what changed, what was added, what was deferred).
4. **Write `work-state.md`** — capture:
   - Active branch(es) and uncommitted state at session end (`git status --porcelain` snapshot).
   - Files created/modified this session, with a one-line purpose each.
   - Concrete next actions (what would I do first if I picked this up tomorrow?).
   - Known blockers or external dependencies.
5. **Update the roadmap doc** if scope, phase boundaries, or non-goals changed during the session. Session notes capture deliberation; roadmap captures the decision.
6. **Surface a commit reminder** to Romano listing the new session files and any roadmap doc changes. Atlas does not commit.

`scratch.md` is optional. Use it only when you actually generated ephemeral notes worth preserving but not worth promoting to context.

## Beginning-of-Session Protocol

1. **Git state guard** — Run `git status --porcelain` in the active repo and any other repo the project lists as in-scope (e.g., valuelens depends on doppiozero, so check both). If uncommitted changes exist, surface as a blocking notice:

   ```
   Uncommitted changes detected:
   - <repo>: <N files> (list modified/untracked)
   Recommend: commit or stash before proceeding.
   ```

2. **Load recent sessions** — Read the last 3 dated folders under `<active-repo>/sessions/`. For each, load `atlas-context.md` and `work-state.md`. Skip any folder lacking both files.

3. **Load roadmap doc** — Read the project roadmap referenced in the loaded sessions' frontmatter (or the obvious match if none specified).

4. **Repo state snapshot** — `git log --oneline -10` and current branch in each in-scope repo. Compare against the most recent `work-state.md` to detect drift (e.g., branch was merged, files were further changed outside Atlas, etc.).

5. **Brief Romano** — Concise summary:
   - Project + current phase per roadmap.
   - Last session's outcome and stated next action.
   - Open questions still unanswered.
   - Drift flags, if any.
   - Confirm priority for this session.

Keep the brief tight (≤200 words). Romano can ask for elaboration.

## Project Anchoring (on "continue X" / "resume X")

When Romano's opening message names a project:

1. **Locate roadmap doc** — Search the active repo (and `00-fin/docs/` if working under `00-fin`) for `*<slug>*roadmap*.md` or `*<slug>*.md`. Fuzzy match if needed.
2. **Identify in-scope repos** — From the roadmap doc's "Depends on" / "Location" sections.
3. **Run beginning-of-session protocol** scoped to those repos.
4. **Surface drift** — Compare roadmap claimed phase/status against actual repo state (commits since last session, branches, file presence). Flag mismatches before treating any "in progress" claim as current.

## Querying Memory

There is no semantic index. To find past context:

- **Recent (last ~7 days):** read `sessions/` directly.
- **Older:** use `grep_search` over `<repo>/sessions/**/*.md` with the keyword. Roadmap docs and session frontmatter make targeted searches cheap.
- **Cross-repo:** repeat per repo. If this becomes painful, that is the signal to invest in an index; do not build one preemptively.

## What Atlas-Memory Does NOT Do

- No task queue. Use the roadmap doc's Phase sections as the task list. Open questions live in `atlas-context.md`.
- No semantic index, no embeddings, no rebuild scripts.
- No briefing automation beyond reading the last 3 sessions.
- No cross-repo aggregation. Each repo's sessions are self-contained.
- No commits. Romano commits session notes himself.

If any of these become a real bottleneck, propose adding it explicitly. Do not add infra speculatively.

## See Also

- **Code loop orchestration**: `atlas-code-loop` skill
- **Atlas operating principles**: `doppiozero/.github/agents/atlas.agent.md`
- **Argus equivalent (work projects)**: `gh-brain/.github/skills/argus-memory/SKILL.md`
