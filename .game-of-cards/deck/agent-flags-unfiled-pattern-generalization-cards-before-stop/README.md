---
title: agent-flags-unfiled-pattern-generalization-cards-before-stop
summary: "A Claude Code Stop hook that asks the agent to self-review whether its recent change was a small instance of a broader pattern that deserves its own generalization card. The pattern surfaced this turn (install.py:598 hint redirect → broader cli-output-suggests-next-step-after-each-verb card filed by hand): agents do narrow work that ought to spawn generalization cards but rarely do unless the human prompts. The hook would close that gap automatically."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Hook implementation matches the chosen design (see Decision required) and ships under `goc/templates/hooks/` so `goc install --agents claude` picks it up
  - [ ] Hook fires only on stops that follow a code-mutating tool sequence (not on Q&A turns or pure-conversation stops)
  - [ ] When the hook fires and the agent's response indicates "yes, a generalization is warranted," the agent is expected to file via `Skill(create-card)` before yielding; the hook's prompt explicitly says so
  - [ ] False-positive rate measured on at least 5 real sessions and judged acceptable, OR hook is gated behind an opt-in setting
  - [ ] `.claude/hooks/` consumer copy in this repo updated alongside the template (per CLAUDE.md's lockstep edit rule until next `goc upgrade`)
  - [ ] AGENTS.md / CLAUDE.md mention the hook so users know it exists and how to disable it
  - [ ] `uv run goc validate` passes

# Agent flags unfiled pattern-generalization cards before stop

## Why

The deck methodology assumes persistent work flows through cards. In practice, agents (and humans) often make a narrow change that's an *instance* of a broader pattern without filing the generalization. Examples observed in this repo's own session history:

- `goc/install.py:598` — a single `Next:` hint added to one verb's output. The broader pattern (every state-mutating verb should print such a hint) needed a separate card (`cli-output-suggests-next-step-after-each-verb`) filed by the human afterwards.
- The `assets/` folder added without a card; the asset card existed already, but the bookkeeping was implicit. Easy to imagine a less-attentive run leaving the card un-updated.

The failure mode is silent: the narrow work ships, the broader work evaporates with the conversation, and the next agent in the codebase has no signal that there's an open pattern to extend.

A Claude Code **Stop** hook is the natural automation point. Stop hooks fire when the agent yields control, can inject system reminders, and can BLOCK the stop and force a continuation. That's the right surface for "before yielding, did you forget to file a card?"

## Design space (Decision required)

Three axes need a human pick.

### Axis 1 — detection mechanism

**A. Lightweight prompt-only.** Hook injects a fixed system reminder on stop: *"Before yielding: did your recent commit(s) touch a pattern with broader applicability? If yes, file a generalization card via `Skill(create-card)` before stopping."* The agent self-judges. Cheap, no codebase scan, false-positive rate depends entirely on agent self-honesty.

**B. Heuristic-scanned.** Hook runs a subprocess that greps the most recent commit's diff for "pattern shapes" (e.g., a new `click.echo` line in a file that has many `click.echo` lines without similar additions; a new `def` matching a naming convention applied unevenly). Injects a more targeted prompt naming the suspected pattern. Higher signal, higher build cost, more maintenance.

**C. LLM-judgment subagent.** Hook spawns a sub-LLM call that reads the diff and returns "looks like a pattern instance" / "looks one-off" / "looks like a generalization is already filed". Best signal, highest cost, slowest stops.

### Axis 2 — firing condition

**A. Every stop.** Always inject. Maximal noise.

**B. Only after code-mutating tool calls.** Skip stops on pure-Q&A turns (no Edit/Write/Bash-commit since last user input). Most natural; matches the failure mode.

**C. Only after commits.** Even narrower — only fire when the agent committed during this turn. Misses uncommitted changes but most stable signal.

### Axis 3 — escalation policy

**A. Reminder-only.** Inject a system reminder on stop; agent decides whether to act. If it ignores the reminder, work proceeds without a card.

**B. Block-stop with prompt.** Hook returns the BLOCK signal with a prompt asking the agent to either file a card or explicitly state "no generalization warranted because X". Forces self-articulation. More friction; harder to ignore by accident.

## Recommended starting point (for the human to confirm or override)

If asked to pick, I'd lean toward **A + B + A** (lightweight prompt-only, only after code-mutating tools, reminder-only) as the cheapest experiment that still catches the real failure mode. Promote axes if the false-positive or false-negative rate is unacceptable in practice.

## Notes

- The hook lives in `goc/templates/hooks/` (template surface) AND `.claude/hooks/` (consumer copy in this repo). Per CLAUDE.md, edit both in lockstep until next `goc upgrade`.
- Naming candidates: `pattern-generalization-check.py`, `unfiled-card-check.py`, `before-stop-card-check.py`. Pick during implementation.
- This card is itself an instance of the pattern it proposes to automate — the install.py:598 change was the seed instance of the verb-output pattern, then we hand-filed `cli-output-suggests-next-step-after-each-verb`, and now we're hand-filing this card to automate the hand-filing. Recursive but well-founded.
