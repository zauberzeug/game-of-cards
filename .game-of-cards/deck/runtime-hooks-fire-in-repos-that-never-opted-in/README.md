---
title: runtime-hooks-fire-in-repos-that-never-opted-in
status: open
stage: null
contribution: high
created: "2026-08-13T06:55:08Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
draft: false
definition_of_done: |
  - [ ] TDD: deck_prompt_router.py exits 0 with no output on a work-shaped prompt when the invoking repo has no `.game-of-cards/deck/` directory; a test drives the hook over its stdin contract from a project dir without a deck
  - [ ] TDD: with a deck present, behavior is unchanged (existing router tests stay green)
  - [ ] MECHANICAL: the guard is identical in every shipped copy of the router (claude-plugin, codex-plugin, templates, .claude dogfood dir) per the repo's sync convention
  - [ ] MECHANICAL: docs state the rule — runtime hooks are inert outside opted-in repos; `Skill(kickoff)` / `goc install` remain the only opt-in path
---

# Runtime hooks fire in repos that never opted in

## Summary

The plugin's hooks are registered globally, so they run in **every** repo the user works in — and `deck_prompt_router.py`, alone among them, never checks whether the repo has a deck before acting. On any work-shaped prompt it claims "[Game of Cards | runtime active]" and mandates the silent card pipeline, which makes agents scaffold decks and auto-commit bookkeeping into repos that never chose GoC. Gate the router on the presence of `.game-of-cards/deck/`, the way `deck_session_start.py` already does.

## Location

- `claude-plugin/hooks/deck_prompt_router.py` — `main()` inspects only the prompt text; no deck-presence check before printing `REMINDER`. The only ungated runtime hook.
- Synced copies: `codex-plugin/hooks/`, `*/goc/templates/hooks/`, `.claude/hooks/`.
- The correct pattern already exists next door: `deck_session_start.py:288-294` resolves the project dir from the hook input, checks `.game-of-cards/deck` (with the legacy `deck/` fallback), and returns 0 when absent. `pattern_generalization_check.py` is likewise gated via `.game-of-cards/config.yaml`.

## What's broken

`DECK_LOCATION.md` pins the shipped contract: the deck lives at `Path.cwd() / ".game-of-cards" / "deck"` — "goc reads Path.cwd()". The router never consults it. Its `REMINDER` opens with "[Game of Cards | runtime active]" — a false claim in a repo with no runtime state — and instructs the agent to run scan-deck → create-card → finish-card *silently* ("DO NOT announce card operations"). In a fresh repo, `goc new` happily scaffolds `.game-of-cards/` and later state flips auto-commit, so the methodology installs itself as a side effect of phrasing ("can you fix…"), invisibly to the user.

## Empirical evidence

Observed 2026-08-13 in `zauberzeug/colophon` (public, deliberately-small repo, never kicked off): the router fired on ordinary work prompts, the agent obeyed, and two deck-only commits landed on local `main` (`72b62b8`, `82e9248` there) before the user noticed and asked what `.game-of-cards` was doing in the repo. Cleanup required a `git reset --hard origin/main`. The hook's own silence rule delayed discovery — the user learned about the deck from a stray sentence in a status report, not from the agent.

## Why it matters

Opt-in is the boundary between a methodology and a contagion. A repo owner who installs the plugin for repo A must not find bookkeeping commits in repo B; a public OSS repo must not accrue a private team's work-tracking state because a contributor has the plugin installed. The false "runtime active" claim also poisons agent behavior: the agent trusts the hook over the absent filesystem state. (Kickoff's auto-invoke — "when any GoC skill runs in a repo with no deck" — already covers the intended discovery path: the *user* asking for GoC, not the router asserting it.)

## Fix

Mirror the sibling hook: in `deck_prompt_router.py`'s `main()`, resolve the project dir the same way `deck_session_start.py`'s `_project_dir_from_hook_input()` does (falling back to cwd), and before any output:

```python
if not (Path(project_dir) / ".game-of-cards" / "deck").is_dir():
    return 0
```

Same-repo is the only shipped deck configuration (`DECK_LOCATION.md`: "goc reads `Path.cwd() / '.game-of-cards' / 'deck'`"), so the project dir is the correct anchor; whether the legacy `deck/` fallback belongs here too should follow whatever session-start does. Keep the guard in the shared template so all plugin copies stay in sync, and add the no-deck stdin-contract test beside the existing router tests.
