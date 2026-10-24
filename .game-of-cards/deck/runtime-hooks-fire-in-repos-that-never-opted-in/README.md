---
title: runtime-hooks-fire-in-repos-that-never-opted-in
summary: "deck_prompt_router.py is the only runtime hook that never checks for a deck, so a globally enabled plugin claims \"runtime active\" and drives the silent card pipeline in repos that never opted in. Gate it on `.game-of-cards/deck/` the way deck_session_start.py already does."
status: done
stage: null
contribution: high
created: "2026-08-13T06:55:08Z"
closed_at: "2026-10-24T04:36:23Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: deck_prompt_router.py exits 0 with no output on a work-shaped prompt when the invoking repo has no `.game-of-cards/deck/` directory; a test drives the hook over its stdin contract from a project dir without a deck
  - [x] TDD: with a deck present, behavior is unchanged (existing router tests stay green)
  - [x] MECHANICAL: the guard is identical in every shipped copy of the router (claude-plugin, codex-plugin, templates, .claude dogfood dir) per the repo's sync convention
  - [x] MECHANICAL: docs state the rule — runtime hooks are inert outside opted-in repos; `Skill(kickoff)` / `goc install` remain the only opt-in path
worker: {who: "claude[bot]", where: main}
---

# Runtime hooks fire in repos that never opted in

## Summary

The plugin's hooks are registered globally, so they run in **every** repo the user works in — and `deck_prompt_router.py`, alone among them, never checks whether the repo has a deck before acting. On any work-shaped prompt it claims "[Game of Cards | runtime active]" and mandates the silent card pipeline, which makes agents scaffold decks and auto-commit bookkeeping into repos that never chose GoC. Gate the router on the presence of `.game-of-cards/deck/`, the way `deck_session_start.py` already does.

## Location

- `claude-plugin/hooks/deck_prompt_router.py` — `main()` inspected only the prompt text, with no deck-presence check before printing `REMINDER`. It was the only ungated runtime hook (source of truth: `goc/templates/hooks/deck_prompt_router.py`).
- Synced copies: `codex-plugin/hooks/`, `*/goc/templates/hooks/`, `.claude/hooks/`.
- The correct pattern already exists next door: `deck_session_start.py:288-294` resolves the project dir from the hook input, checks `.game-of-cards/deck` (with the legacy `deck/` fallback), and returns 0 when absent. `pattern_generalization_check.py` is likewise gated via `.game-of-cards/config.yaml`.

## What's broken

`DECK_LOCATION.md` pins the shipped contract: the deck lives at `Path.cwd() / ".game-of-cards" / "deck"` — "goc reads Path.cwd()". The router never consults it. Its `REMINDER` opens with "[Game of Cards | runtime active]" — a false claim in a repo with no runtime state — and instructs the agent to run scan-deck → create-card → finish-card *silently* ("DO NOT announce card operations"). At filing time, `goc new` in a fresh repo happily scaffolded `.game-of-cards/` and later state flips auto-committed, so the methodology installed itself as a side effect of phrasing ("can you fix…"), invisibly to the user. (`goc new` has since learned to refuse without a deck and to point at `goc install` / `Skill(kickoff)`. The false claim still sent agents down that path.)

## Empirical evidence

Observed 2026-08-13 in `zauberzeug/colophon` (public, deliberately-small repo, never kicked off): the router fired on ordinary work prompts, the agent obeyed, and two deck-only commits landed on local `main` (`72b62b8`, `82e9248` there) before the user noticed and asked what `.game-of-cards` was doing in the repo. Cleanup required a `git reset --hard origin/main`. The hook's own silence rule delayed discovery — the user learned about the deck from a stray sentence in a status report, not from the agent.

## Why it matters

Opt-in is the boundary between a methodology and a contagion. A repo owner who installs the plugin for repo A must not find bookkeeping commits in repo B; a public OSS repo must not accrue a private team's work-tracking state because a contributor has the plugin installed. The false "runtime active" claim also poisons agent behavior: the agent trusts the hook over the absent filesystem state. (Kickoff's auto-invoke — "when any GoC skill runs in a repo with no deck" — already covers the intended discovery path: the *user* asking for GoC, not the router asserting it.)

## Fix

Applied in `goc/templates/hooks/deck_prompt_router.py` and synced to all five mirrors (`claude-plugin/hooks/`, `codex-plugin/hooks/`, both payloads' `goc/templates/hooks/`, `.claude/hooks/`):

- The router now carries the same `_find_project_dir` mirror as its two siblings, spliced in byte for byte. That mirror applies the shared-deck worktree redirect, then the nearest-ancestor walk that stops at a foreign git tree. A session started in a subdirectory of an opted-in repo keeps its reminder. A foreign repo nested inside one does not inherit it. `tests/test_project_root_from_subdirectory.py` now pins all three hooks' mirrors to `engine._resolve_deck_root` (`HookProjectDirWalkTest.HOOK_NAMES`).
- `main()` takes the project dir from the same inputs, in the same order, as the session-start hook. That is the hook input's `cwd` (a non-string is ignored), then `CLAUDE_PROJECT_DIR` / `CODEX_PROJECT_DIR`, then the process cwd. It prints `REMINDER` only when the resolved root holds `.game-of-cards/deck/` or the legacy `deck/` (`_has_deck`), which is the pair session-start reads. That answers the filing's open question about the legacy fallback. The lookup runs only for a work-shaped prompt, so no other prompt pays for the git probes.
- `tests/test_prompt_router_opt_in.py` drives the hook over its stdin contract. It must stay silent without a deck, in a foreign repo nested in an opted-in one, and whenever the payload `cwd`, the project-dir variable, or the process cwd names a deckless root. The reminder, unchanged, must appear in an opted-in repo, in its subdirectory, and in a legacy-`deck/` repo. Six of its nine tests fail against the pre-fix router. The three reminder cases pass on both.
- The rule is stated in AGENTS.md (hook section), `goc.md`, `claude-plugin/README.md` and `codex-plugin/README.md`.

The OpenClaw TypeScript port (`before_prompt_build` in `openclaw-plugin/index.ts`) has the same gap. Fixing it needs a `dist/` rebuild, so it is filed as [openclaw-prompt-hook-fires-in-workspaces-without-a-deck](../openclaw-prompt-hook-fires-in-workspaces-without-a-deck/).
