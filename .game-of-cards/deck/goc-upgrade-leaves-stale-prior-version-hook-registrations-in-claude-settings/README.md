---
title: goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings
summary: "Both settings-side functions (`_merge_claude_settings`, `_strip_goc_settings_entries` in install.py) identify a GoC-owned hook registration by its exact *current* command string from `GOC_CLAUDE_HOOKS.values()`. A hook GoC shipped under a different command string in a prior version (the consequence of renaming or repathing a hook file) is invisible to both: merge appends the current registration as a duplicate while the stale one survives, and strip leaves the stale one behind. Fix both sites via one shared GoC-owned-hook discriminator."
status: open
stage: null
contribution: medium
created: "2026-06-08T05:22:40Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: regression test seeds `.claude/settings.json` with a stale prior-version GoC SessionStart registration (command string NOT in `GOC_CLAUDE_HOOKS.values()`) plus the current one, runs `_merge_claude_settings`, and asserts the stale registration is gone (today it survives AND the current one is appended as a duplicate).
  - [ ] TDD: regression test seeds settings.json with ONLY a stale prior-version GoC registration, runs `_strip_goc_settings_entries`, and asserts the stale registration is removed (today it survives — strip keys on current `GOC_CLAUDE_HOOKS.values()` only).
  - [ ] TDD: regression test asserts a genuinely user-authored hook registration (a command that was never GoC-shipped) survives BOTH merge and strip — the discriminator must not over-reach into user content.
  - [ ] PROCESS: decision recorded in a `## Decision (recorded)` section — which mechanism identifies a GoC-owned hook command across versions, and whether it is shared with the file-cleanup sites in [goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/).
  - [ ] MECHANICAL: fix implemented at both settings-side sites (`_merge_claude_settings` dedup/replace, `_strip_goc_settings_entries` removal) sharing one helper; `uv run python scripts/sync_plugin_assets.py --check` clean.
  - [ ] PROCESS: `uv run goc validate` passes; full unittest regression suite passes.
---

# `goc upgrade` leaves stale prior-version hook registrations in `.claude/settings.json`

## Location

- `goc/install.py:607-651` — `_merge_claude_settings`, the dedup-and-append loop.
- `goc/install.py:656-770` — `_strip_goc_settings_entries`, the removal pass.
- `goc/install.py:539-543` — `GOC_CLAUDE_HOOKS`, the **current**-version event→command map both sites key on.

## What's broken

Both settings-side functions identify a GoC-owned hook registration by its
**exact current command string** drawn from `GOC_CLAUDE_HOOKS.values()`. Any
hook GoC shipped under a *different* command string in a prior version — the
direct consequence of renaming or repathing a hook file — is invisible to both
the dedup and the removal logic.

**Merge side** (`_merge_claude_settings`), the dedup at `install.py:644`:

```python
already = any(
    isinstance(h, dict) and h.get("command") == command   # exact current-string match
    for group in event_hooks
    if isinstance(group, dict) and isinstance(group.get("hooks"), list)
    for h in group["hooks"]
)
if not already:
    event_hooks.append({"hooks": [{"type": "command", "command": command}]})
```

A stale prior-version registration does not equal `command`, so `already` is
`False` and the current command is **appended as a second group** — leaving
both the stale and the current registration live.

**Strip side** (`_strip_goc_settings_entries`), `install.py:678` + `736`:

```python
goc_commands = set(GOC_CLAUDE_HOOKS.values())   # current strings only
...
if h.get("command") in goc_commands:
    removed_any = True
    continue
```

A stale prior-version command is not in `goc_commands`, so the strip pass
preserves it verbatim — the cleanup that is supposed to remove GoC-managed
entries cannot.

This is the **settings.json-registration sibling** of the file-cleanup defect
already catalogued in
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/),
which documents the same prior-version blindness at three *file*-level sites
(`_strip_claude_vendored_harness` skills loop, its hooks loop, and
`_sync_skill_tree(replace_skills=True)`). That card's DoD promises a shared
identification helper "implemented at all three sites" — but it enumerates only
the file-removal sites; the two settings.json *registration* sites here are a
fourth and fifth instance of the same root-cause shape and are not covered by
its current scope.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings/reproduce.py`
(exits non-zero today):

```
merge: SessionStart commands after merge = ['python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/OLD_deck_session_start.py', 'python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/my_own_hook.py', 'python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py']
strip: SessionStart commands after strip = ['python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/OLD_deck_session_start.py', 'python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/my_own_hook.py']

BUG: stale prior-version registration survived merge
BUG: stale prior-version registration survived strip

DEFECT PRESENT
```

The stale `OLD_deck_session_start.py` registration survives both passes; the
current `deck_session_start.py` command is appended alongside it on merge. The
user-authored `my_own_hook.py` registration is correctly left intact by both —
confirming the bug is prior-version blindness, not over-reach.

## Why it matters

- **Reachability.** The offending input — a settings.json carrying a GoC hook
  command string from a prior GoC version — is produced by exactly the flow the
  sibling card already treats as real: a future GoC release renames a hook file
  (the sibling cites the shipped `bootstrap/` → `kickoff/` precedent for skills),
  changing `GOC_CLAUDE_HOOKS[<event>]`. On the next `goc upgrade`,
  `_merge_claude_settings` runs over the consumer's existing settings.json and
  hits this path. No hand-editing required.
- **Double-firing.** A surviving stale registration plus a still-present stale
  hook file (the file-cleanup card's bug) means Claude Code runs *both* the old
  and the new hook on every matching event — duplicated SessionStart reminders,
  or a deck_prompt_router that fires twice per prompt.
- **Silent accumulation.** Like the file-cleanup sites, nothing warns; the
  cruft grows one entry per renamed hook per upgrade and never self-heals.

## Decision required

The fix needs the same judgement the file-cleanup sibling needs: **how does the
engine recognise a GoC-owned hook command independent of its current string?**
Options:

- **A — inherit the sibling's chosen mechanism.** Whatever discriminator
  `goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install`
  lands (sentinel marker / historical-name registry / path-shape heuristic),
  apply it to the two settings-side sites via the same shared helper. Preferred
  if the sibling lands first — one mechanism, five sites, no drift.
- **B — historical command/path registry.** Maintain an explicit set of
  prior-version hook command strings (or a regex over the
  `.claude/hooks/<name>.py` path shape) that merge dedups against and strip
  removes, in addition to the current set.
- **C — path-shape heuristic only.** Treat any command matching
  `python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/*.py` as GoC-managed for
  dedup/removal. Simplest, but risks reaching into a user-authored hook that
  happens to live under `.claude/hooks/`.

Whichever is chosen, the regression tests must prove a genuinely user-authored
registration survives untouched (the discriminator must not over-reach — the
exact failure mode the file-cleanup card's predecessor
`goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode` was
filed to prevent).

## Fix

Deferred to the decision above. The two call sites and the shared
`GOC_CLAUDE_HOOKS` key set are quoted under "What's broken"; the fix is a single
shared identification helper consulted by both, plus (on the merge side)
replacing a matched stale group's command rather than appending a duplicate.
**Do not apply until the mechanism is decided.**
