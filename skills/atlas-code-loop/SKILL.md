# Atlas Code Loop Skill

Orchestrates the adversarial code loop between atlas-architect (design intent and critique) and atlas-coder (implementation), with Atlas as the orchestrator. Supports two modes: supervised (default) and autonomous.

This is the personal-projects analog of `argus-code-loop`. Use it for non-trivial, plan-anchored, PR-sized python work on personal repos. Do not use it for trivial edits or for architectural decisions Romano has not yet made.

## Architecture

- **`@atlas`**: Orchestrator. Calls subagents, manages the loop, runs verification (tests, lint), enforces gates.
- **`@atlas-architect`**: Owns design intent. Produces briefs, critiques implementation against its own briefs, declares convergence.
- **`@atlas-coder`**: Implements briefs. Code edits only; never runs verification.
- **`@atlas-reviewer`**: Mandatory post-convergence pass in autonomous mode. Independent critic that did not participate in the loop.

## Trigger Phrases

- "code loop supervised", "step by step on this change", "walk me through this"
- "code loop autonomous", "auto mode", "hands off", "just build it"
- "atlas code loop"

## When To Use This Skill

Use it when **all** of the following hold:

- The work is a single, well-scoped PR-sized chunk (one or a few files).
- A Plan of Record item exists that names this work (project doc section, issue, or explicit Romano scope statement from this session).
- The design is mostly decided; the work is shape + implementation, not new architecture.

**Do NOT use it for:**

- Trivial edits (typos, single-line fixes, mechanical refactors). Atlas handles directly.
- Open architectural decisions Romano has not yet made. Atlas surfaces options and waits.
- Cross-cutting changes spanning many files or multiple plan items. Split first.

## Pre-flight Gates

Before invoking the loop, Atlas must verify and state out loud:

1. **Plan anchor.** Name the Plan of Record item this work serves. If no item maps, stop and ask Romano whether to update the plan or rescope.
2. **Mode.** Default to supervised. Autonomous mode requires Romano to have used an autonomous trigger phrase AND a named plan anchor.
3. **Scope statement.** One sentence: "This loop will produce X in files Y, gated on Z."

If any pre-flight check fails, do not invoke the loop. Ask Romano to clarify.

## Modes

### Supervised Mode (default)

Romano sits between each exchange.

**Loop:**

1. Atlas gathers context (project doc, target directory, existing patterns, relevant skill files).
2. Atlas calls `runSubagent(agentName: "atlas-architect")` to produce a brief.
3. Atlas presents the brief to Romano.
4. **GATE: Romano approves, adjusts, or rejects.**
5. Atlas calls `runSubagent(agentName: "atlas-coder")` with the approved brief.
6. Atlas runs verification: `poetry run pytest <relevant paths>`, `poetry run flake8`, and any repo-specific checks. Reports results.
7. Atlas calls `runSubagent(agentName: "atlas-architect")` for critique, passing the diff and test results.
8. Atlas presents critique to Romano.
9. **GATE: Romano approves iteration, adjusts, or declares done.**
10. If iterating, go to step 5 with the refined brief.
11. Final delivery: present the completed work with summary of decisions and any accepted tradeoffs.

### Autonomous Mode

Romano provides a scoped, plan-anchored prompt. Atlas runs the loop without intervention until convergence or the iteration cap, then runs an independent reviewer pass before presenting.

**Loop:**

1. Atlas gathers context.
2. Atlas calls `runSubagent(agentName: "atlas-architect")` for the initial brief.
3. Atlas calls `runSubagent(agentName: "atlas-coder")` with the brief.
4. Atlas runs verification (tests + lint). If hard failures, feed them into the next critique round.
5. Atlas calls `runSubagent(agentName: "atlas-architect")` for critique.
6. **Convergence check** (see below).
7. If not converged: refined brief, back to step 3.
8. If converged: **mandatory independent review.** Atlas calls `runSubagent(agentName: "atlas-reviewer")` on the full diff. This reviewer did not see the brief and is not bound by it.
9. Atlas presents to Romano: the diff summary, the architect's convergence note, and the reviewer's findings.

**Convergence criteria (whichever hits first):**

- **Architect says Pass.** No substantive deviations from the brief, tests green, lint clean.
- **Iteration cap:** Maximum 3 rounds of code-verify-critique-refine.

**Hard stops (even in autonomous mode, pause and ask Romano):**

- Pre-flight gate failure (no plan anchor, ambiguous scope).
- Verification fails for a reason the brief did not anticipate.
- atlas-coder reports a technical blocker that invalidates the brief.
- atlas-architect requests a brief revision driven by a design realization.
- Scope creep: implementation naturally requires touching files outside the brief's file list.

## Brief Format (atlas-architect to atlas-coder)

```
## Brief

**Plan anchor:** [Project doc + section]
**Scope:** [One sentence; what's in. Followed by what's explicitly out.]

**Files:**
- create: [exact path]
- modify: [exact path]

**Interface spec:**
- [Class/method signature, with argument names and types]
- [Key constants, error classes, return shapes]

**Test cases:** (each bullet = one assertion, with target file)
- [tests/path/test_x.py] asserts [behavior] given [input]
- ...

**Conventions:**
- Follow [skill file path] for [aspect]
- Match existing pattern in [reference file]

**Acceptance criteria:**
- [ ] [Verifiable condition]
- [ ] All listed tests pass
- [ ] Lint clean

**Out-of-scope guardrails:**
- Do not modify [tempting but out-of-scope file]
- Do not introduce [tempting but out-of-scope abstraction]
```

## Critique Format

Output exactly one of:

- **Pass.** One sentence justification.
- **Refine.** Bulleted deviations (what's wrong, why it matters, exact change needed) plus a refined brief delta.
- **Brief revision needed.** Explanation, then a revised brief. Do not blame the coder for following the original.

## Guardrails

- **Verification ownership.** Only Atlas runs `pytest`, `flake8`, or any terminal command. Never the subagents.
- **No destructive changes in autonomous mode.** Escalate.
- **File-list discipline.** atlas-coder must not touch files outside the brief's file list. If it does, atlas-architect flags it.
- **Max files per brief:** 5. Split if larger.
- **Romano owns the critical path.** No commits, pushes, merges. Staged changes only.
- **No silent plan drift.** If the work requires a Plan of Record change, stop and surface it.
