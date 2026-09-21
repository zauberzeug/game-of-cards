---
title: nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries
summary: "CONFIRMED and FIXED. AGENTS.md said the hook event mapping stays hand-written in three registries because a command is not derivable from a script name, and that `goc validate` covers all three; it covered only the script *set*, so a script bound to the wrong event in one payload passed every tripwire and failed only at runtime, silently. `reproduce.py` drove three mis-bindings — a payload event swap, an event no registry knows, and a `GOC_CLAUDE_HOOKS` swap — and all three returned `[]` from both validators. The fix makes the event half part of the checked contract: `_plugin_registered_hook_bindings` returns `(event, script)` pairs and `validate_plugin_hook_registration` compares them against `GOC_CLAUDE_HOOKS`, read through one shared `claude_hook_bindings()` walk."
status: done
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: "2026-09-21T05:31:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] EMPIRICAL: the falsification recipe below is run and its verdict recorded in `log.md` either way — swap two events in one `hooks.json` and report whether `validate_plugin_hook_registration` returns a non-empty error list.
  - [x] TDD: if the gap is confirmed, `reproduce.py` exits zero once a mis-bound event is detected, having exited 1 before the fix; the `unverified` tag is dropped at that point.
  - [x] MECHANICAL: the event half of the registration becomes part of the checked contract — `_plugin_registered_hook_scripts` returns `(event, script)` pairs and `validate_plugin_hook_registration` compares them against `GOC_CLAUDE_HOOKS` as the reference mapping.
  - [x] TDD: `tests/test_plugin_hook_json_registration.py` stops registering its fixture under synthetic `Event{i}` names for the assertions that now depend on the event, so the fixture exercises the contract rather than working around it.
  - [x] PROCESS: `AGENTS.md`'s claim that "`goc validate` covers all three" is narrowed or the code widened to match it — whichever the fix picks, the sentence and the code agree afterwards.
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Nothing checks which event a hook is bound to across the three registries

**Confirmed, then fixed.** `reproduce.py` is the falsification run the card was
filed without: three separately-planted mis-bindings, all three unreported by
both validators before the fix, all three reported after. The card was filed
`unverified` off a static read; the run confirmed the read exactly.

## The gap

`AGENTS.md` states the contract:

> The **event mapping** is not derived — it stays explicit in three
> hand-maintained registries, one per install path: `GOC_CLAUDE_HOOKS`
> (`goc/install.py`, the vendored `--local-skills` path) plus
> `claude-plugin/hooks/hooks.json` and `codex-plugin/hooks/hooks.json`. …
> `goc validate` covers all three.

The three registries did agree. Nothing checked that they kept agreeing on the
*event*. `_plugin_registered_hook_scripts` iterated the events and returned
only script basenames — `event` reached the error strings for malformed shapes
and nowhere else — and the parity check that consumed them was a two-way set
difference over those names. So "every shipped script is registered somewhere,
and every registration names a shipped script" was enforced; "this script is
bound to the event it is written for" was not. `scripts/sync_plugin_assets.py`
could not cover the gap either: `hooks.json` sits in that script's
`preserve_files` set and is never compared.

`tests/test_plugin_hook_json_registration.py` registered its fixture under
synthetic `Event{i}` names, which was the clearest statement that the event sat
outside the contract under test — and the reason the rewrite of that fixture is
its own DoD item rather than incidental churn.

The script half of this contract was built deliberately and closed twice:
[plugin-payload-hooks-json-never-registers-a-newly-added-hook-script](../plugin-payload-hooks-json-never-registers-a-newly-added-hook-script/)
(done) added the two-way shipped-versus-registered difference, and
[derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
(done) made the *list* derived rather than restated. Both are scoped to which
scripts exist. Neither touched which event a script is bound to — the one half
AGENTS.md says cannot be derived, and therefore the half that has to be checked
rather than generated.

## Verdict

`reproduce.py` builds a throwaway `REPO_ROOT`-shaped tree per case and runs
`validate_hook_registration` + `validate_plugin_hook_registration` over it:

| Case | Before | After |
|---|---|---|
| codex payload swaps `SessionStart` and `Stop` | both validators returned `[]` | 2 errors |
| claude payload binds the primer to `Resume`, an event nothing else names | both returned `[]` | 1 error |
| `GOC_CLAUDE_HOOKS` swaps the events both payloads agree on | both returned `[]` | 4 errors, one per payload per script |

The third case is the recipe's control — it establishes that the vendored path
was no stronger, and that after the fix a swap authored in *any* of the three
registries surfaces, because the comparison is relative rather than
authoritative. Only an identical simultaneous swap in all three is invisible,
and that is a coordinated edit, not drift.

## Why it mattered

A mis-bound hook is silent in exactly the way the hook system is designed not
to be: `deck_session_start.py` bound to `Stop` prints the active-card reminder
after every turn instead of once at session start, and
`pattern_generalization_check.py` bound to `SessionStart` blocks nothing and
reminds nobody. Both keep exiting 0. The registries are hand-maintained
precisely because the mapping is not derivable — which is also the reason it is
the half most likely to drift, and the half nothing read back.

## Fix

- `goc/install.py` gains `claude_hook_bindings()`: `GOC_CLAUDE_HOOKS` inverted
  to script → the set of events it is bound to, with the unrecognizable-command
  diagnostic it already produced. Both validators now read the registry through
  that one walk — a second hand-rolled parse of a hand-maintained registry is
  the shape this repo already has a card family about.
- `_plugin_registered_hook_scripts` → `_plugin_registered_hook_bindings`,
  returning `(event, script)` pairs. The rename is part of the fix: a function
  named `..._scripts` that returns pairs is the next drift.
- `validate_plugin_hook_registration` compares each payload's event set per
  script against the reference, for scripts both registries name. A script one
  side is missing entirely stays the *script* half's finding — restating it
  under a second diagnosis would bury the one that names the fix.
- `AGENTS.md`'s "covers all three" sentence now states both halves.

The comparison assumes the hosts share an event vocabulary, which they do today
(`SessionStart` / `UserPromptSubmit` / `Stop` in all three registries). A host
that renames an event needs a per-host alias map in
`validate_plugin_hook_registration`; that is a deliberate edit, which is the
point — silent drift is what this rules out.
