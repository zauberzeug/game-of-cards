---
title: skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path
summary: "Six shipped skill templates (audit-deck, pull-card, next-card, refine-deck, retrospective, standup) run bare `goc` in their `!`-preamble shell blocks. On any host where `goc` is not on PATH, an unguarded block exits 127 and Claude Code aborts the whole skill load — the skill body, including its own documented `goc: command not found` recovery guidance, never reaches the agent. The `_goc-bootstrap.sh` wrapper shipped by the closed bootstrap-error-when-cli-not-on-path card handles exactly this (missing CLI, plugin bin, dogfood uv), but no `!` block invokes it."
status: done
stage: null
contribution: medium
created: "2026-07-13T01:24:10Z"
closed_at: "2026-07-15T01:05:08Z"
human_gate: none
advances: []
advanced_by:
  - bootstrap-error-when-cli-not-on-path
tags: [bug, api-contract]
definition_of_done: |
  - [x] PROCESS: fix shape decided and recorded inline + in log.md — (a) route every `!` block through the bootstrap wrapper with a bare-`goc` fallback for plugin-mode loads, (b) append `2>&1 || true`-style guards so a missing CLI degrades into the skill body instead of aborting the load, or (c) both.
  - [x] MECHANICAL: every `!`-preamble block across `goc/templates/skills/*/SKILL.md` that invokes `goc` survives a host without `goc` on PATH (load completes; error text lands in the loaded body where the Preflight guidance can route it).
  - [x] EMPIRICAL: in this repo (no bare `goc` on PATH), `Skill(refine-deck)` loads instead of erroring `Shell command failed for pattern`; observed output recorded in log.md.
  - [x] TDD: a regression test asserts no skill template contains an unguarded bare-`goc` `!` block (greps the template tree for the antipattern the chosen fix eliminates).
  - [x] MECHANICAL: plugin mirrors regenerated (`pre-commit run --all-files` / `python scripts/sync_plugin_assets.py --check` clean); `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Skill preamble `!` blocks call bare `goc` and abort skill load when the CLI is off PATH

## Observed failure (this repo, 2026-07-13)

Invoking `Skill(refine-deck)` in this repository on a cloud runner
returned a tool-level error instead of loading the skill:

```
Shell command failed for pattern "!`goc --tag unverified -v`": [stderr]
/bin/bash: line 1: goc: command not found
```

The skill never loaded. The agent had to open
`.claude/skills/refine-deck/SKILL.md` by hand and simulate the flow —
exactly the degraded mode the methodology is designed to prevent.

## Location

Bare-`goc` `!`-preamble blocks in six shipped templates (consumer
mirrors under `.claude/skills/` inherit them):

- `goc/templates/skills/refine-deck/SKILL.md:55,71,90` — line 55 is
  guarded (`|| echo …`); 71 and 90 are not.
- `goc/templates/skills/audit-deck/SKILL.md:19,21,23`
- `goc/templates/skills/pull-card/SKILL.md:30,42`
- `goc/templates/skills/next-card/SKILL.md:17,19`
- `goc/templates/skills/retrospective/SKILL.md:17`
- `goc/templates/skills/standup/SKILL.md:20,22,24`

`goc/templates/bootstrap/_goc-bootstrap.sh` — the wrapper that already
solves CLI resolution: exec's `goc` when on PATH, discovers a plugin
`bin/goc` relative to itself, falls back to `uv run` inside this
dogfood repo (detects `name = "game-of-cards"` in `pyproject.toml`),
and prints the one-line pipx install hint with exit 127 when nothing
resolves. Only `codex-kickoff/SKILL.md` references it, and only in
prose — no `!` block anywhere invokes it.

## What's broken

Two stacked defects:

1. **The bootstrap guarantee regressed.** The closed
   [bootstrap-error-when-cli-not-on-path](../bootstrap-error-when-cli-not-on-path/)
   card's DoD asserts every skill invokes
   `.claude/skills/_goc-bootstrap.sh` instead of `goc` directly. The
   `!`-preamble blocks (added to skills after that card closed) call
   bare `goc`, so the "clean one-line install hint instead of a cryptic
   shell error" guarantee no longer holds for skill *load*.
2. **The documented recovery is unreachable.** `refine-deck`'s
   Preflight section says: "If any `!` block below shows
   `goc: command not found` … invoke `Skill(kickoff)` first." That
   assumes the error text surfaces *into* the loaded skill body. In
   Claude Code, an unguarded `!` block that exits non-zero aborts the
   entire skill load, so the body carrying the recovery instructions is
   never delivered. The soft-gate design (refine-deck Step 1 comment:
   "intentionally soft-gated so a failing validator surfaces its output
   *into* this skill") is implemented for `goc validate`'s exit code
   but not for command-not-found on the other blocks.

## Reachability

- **This dogfood repo:** bare `goc` is never on PATH (AGENTS.md
  mandates `uv run goc`), so all six skills are unloadable here despite
  the bootstrap wrapper's explicit `uv` branch. Every autonomous
  runner session that starts with a Skill invocation hits it.
- **Consumer repos, vendored mode, fresh machine:** clone before
  `pipx install game-of-cards` — the precise cohort the bootstrap card
  was filed for. Skill load aborts with the same cryptic error.
- **Plugin mode:** unaffected — Claude Code prepends the plugin's
  `bin/` to PATH, so bare `goc` resolves.

## Fix shape (decided 2026-07-15: (c) both)

Every goc-invoking `!` fence across the six templates now reads:

```
b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b <args>; else goc <args>; fi 2>&1 || true
```

- **Routing (a):** the `[ -f ]` test picks the *vendored, cwd-relative*
  bootstrap when it exists (vendored installs, this dogfood repo — where
  it resolves PATH goc / plugin bin / `uv run goc` and prints the pipx
  hint when nothing resolves) and falls back to bare `goc` in plugin
  mode, where Claude Code prepends the plugin's `bin/` to PATH and no
  vendored copy exists. A file-existence test rather than
  `2>/dev/null ||` chaining so a real goc failure is never followed by a
  misleading second invocation. The cwd-relative-only reference
  preserves the plugin-policy contract in `test_install.py` (never
  execute scripts from a plugin cache directory) — that test now pins
  the refined invariant.
- **Guard (b):** trailing `2>&1 || true` (or the pre-existing
  `|| echo`/`| head` forms) keeps the fence at exit 0, so a missing CLI
  degrades into error text inside the loaded body — where the Preflight
  section routes the reader to `Skill(kickoff)` — instead of aborting
  the load before that guidance is delivered.
- The OpenClaw porter unwraps the routing back to the bare command
  (`goc` is a registered tool there, not a shell binary), keeping the
  ported skills host-idiomatic.
- Regression guard: `tests/test_skill_preamble_blocks.py` enforces
  routing statically and executes every extracted fence with a failing
  `goc` stub (with and without the bootstrap present), asserting exit 0.
