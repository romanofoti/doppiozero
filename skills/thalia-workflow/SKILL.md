# Thalia Workflow Skill

Orchestrates the adversarial design loop between thalia-des (creative director) and thalia-dev (frontend developer), with Thalia as the orchestrator. Supports two modes: supervised and autonomous.

## Architecture

- **`@thalia`** — Orchestrator. Has `agent` tool, calls subagents, manages the loop.
- **`@thalia-des`** — Creative director. Proposes direction, writes briefs, critiques results.
- **`@thalia-dev`** — Frontend developer. Implements briefs, provides technical assessment.

## Trigger Phrases

- "design this supervised", "step by step", "walk me through"
- "design this autonomously", "auto mode", "hands off", "just do it"
- "thalia workflow"

## Modes

### Supervised Mode (default)

Romano sits between each exchange, approving direction and greenlighting iteration.

**Loop:**
1. Thalia gathers context (reads existing code, styles, structure)
2. Thalia calls `runSubagent(agentName: "thalia-des")` to generate creative direction
3. Thalia presents direction to Romano
4. **GATE: Romano approves, adjusts, or rejects**
5. Thalia calls `runSubagent(agentName: "thalia-dev")` with the approved brief
6. Thalia calls `runSubagent(agentName: "thalia-des")` to critique the implementation
7. Thalia presents critique to Romano with proposed refinements
8. **GATE: Romano approves iteration, adjusts, or declares done**
9. If iterating, go to step 5 with refined brief
10. Final delivery: present completed work with summary of decisions made

### Autonomous Mode

Romano provides a loose prompt. Thalia orchestrates the full loop without intervention. Presents the final result when converged.

**Loop:**
1. Thalia gathers context (reads existing code, styles, structure)
2. Thalia calls `runSubagent(agentName: "thalia-des")` to generate creative direction from Romano's prompt
3. Thalia calls `runSubagent(agentName: "thalia-dev")` with the brief
4. Thalia calls `runSubagent(agentName: "thalia-des")` to critique the implementation
5. **Convergence check** (see below)
6. If not converged: thalia-des produces refined brief, Thalia calls thalia-dev again, go to step 4
7. If converged: present final result to Romano

**Convergence criteria (whichever hits first):**
- **Self-satisfaction:** Thalia's critique has no substantive objections. Minor nitpicks don't count. The question is: "Would I be embarrassed to show this to Romano?"
- **Iteration cap:** Maximum 3 rounds of implement-critique-refine. After 3 rounds, present the best result with a note on what remains imperfect.

**Escalation (even in autonomous mode, pause and ask Romano):**
- Ambiguity in the original prompt that would produce materially different outcomes
- A fundamental technical blocker reported by thalia-dev that requires a design pivot
- Scope creep: if the natural solution requires changes far beyond what the prompt implied

## Invocation

Both modes are invoked through `@thalia` directly. Thalia has the `agent` tool and orchestrates both subagents.

**From Romano to @thalia:**
- "Redesign the hero section" → supervised (default)
- "Redesign the hero section, auto mode" → autonomous
- "Step by step, improve the footer" → supervised
- "Hands off: improve the mobile nav" → autonomous

### Shorthand Reference

| Phrase | Mode |
|--------|------|
| "redesign X" | Supervised |
| "step by step" | Supervised |
| "auto mode" / "hands off" / "just do it" | Autonomous |

## Brief Format (thalia-des to thalia-dev)

Each delegation to thalia-dev must include:

```
## Brief

**Task:** [What to build/change]
**Files:** [Exact file paths to create or modify]
**Design spec:**
- [Concrete values: colors, spacing, fonts, breakpoints]
- [Layout structure description]
- [Interaction behavior if applicable]

**Acceptance criteria:**
- [ ] [Specific, verifiable condition]
- [ ] [Another condition]

**Context:** [Why this matters for the overall design]
```

## Critique Format (thalia-des reviewing thalia-dev output)

After each implementation round, thalia-des evaluates against:

1. **Faithfulness:** Does the code match the brief's design spec?
2. **Visual coherence:** Does it fit with the rest of the site/project?
3. **Hierarchy:** Is the content hierarchy clear and intentional?
4. **Responsiveness:** Will this work across viewports?
5. **Accessibility:** Any obvious a11y gaps?

Critique output:
- **Pass:** No substantive objections. Converged.
- **Refine:** List specific adjustments with rationale. Feed back into next brief.

## Guardrails

- **No destructive changes in auto mode.** If thalia-dev's implementation would delete significant existing content or restructure beyond the prompt's scope, escalate.
- **Preserve existing functionality.** Design changes must not break working features.
- **Stay in scope.** The prompt defines the boundary. If the "right" solution requires touching unrelated pages/components, flag it rather than expanding silently.
- **Max file changes per round:** If a single brief would touch more than 5 files, split into multiple focused briefs executed sequentially.
