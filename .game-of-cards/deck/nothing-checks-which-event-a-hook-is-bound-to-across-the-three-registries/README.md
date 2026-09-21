---
title: nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries
summary: "AGENTS.md says the hook event mapping stays hand-written in three registries because a command is not derivable from a script name, and that `goc validate` covers all three. It covers only the script *set*: `_plugin_registered_hook_scripts` (engine.py:1520-1543) walks `data['hooks'].items()` but lets `event` reach error strings only, and the parity check at engine.py:1594-1604 compares name sets in both directions. So a script bound to the wrong event in one payload — the session primer on Stop, the prompt router on SessionStart — passes every tripwire and fails only at runtime, silently. Parked unverified: citations read and confirmed, no reproduce.py built this round."
status: active
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: the falsification recipe below is run and its verdict recorded in `log.md` either way — swap two events in one `hooks.json` and report whether `validate_plugin_hook_registration` returns a non-empty error list.
  - [ ] TDD: if the gap is confirmed, `reproduce.py` exits zero once a mis-bound event is detected, having exited 1 before the fix; the `unverified` tag is dropped at that point.
  - [ ] MECHANICAL: the event half of the registration becomes part of the checked contract — `_plugin_registered_hook_scripts` returns `(event, script)` pairs and `validate_plugin_hook_registration` compares them against `GOC_CLAUDE_HOOKS` as the reference mapping.
  - [ ] TDD: `tests/test_plugin_hook_json_registration.py` stops registering its fixture under synthetic `Event{i}` names for the assertions that now depend on the event, so the fixture exercises the contract rather than working around it.
  - [ ] PROCESS: `AGENTS.md`'s claim that "`goc validate` covers all three" is narrowed or the code widened to match it — whichever the fix picks, the sentence and the code agree afterwards.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Nothing checks which event a hook is bound to across the three registries

**Parked `unverified`.** The cited code was read and confirmed in this repo;
no `reproduce.py` was built this round. Surfaced by a hunter agent during an
`Skill(audit-deck)` round, which reported a reproduction of its own (below) —
that report is second-hand here and has not been re-run.

## Hypothesis

`AGENTS.md` states the contract:

> The **event mapping** is not derived — it stays explicit in three
> hand-maintained registries, one per install path: `GOC_CLAUDE_HOOKS`
> (`goc/install.py`, the vendored `--local-skills` path) plus
> `claude-plugin/hooks/hooks.json` and `codex-plugin/hooks/hooks.json`. …
> `goc validate` covers all three.

The three registries do agree today. Nothing checks that they keep agreeing on
the *event*.

`goc/engine.py:1520-1543` — `_plugin_registered_hook_scripts` iterates the
events but returns only script names:

```python
    for event, groups in data["hooks"].items():
        ...
            for entry in entries:
                command = entry.get("command") if isinstance(entry, dict) else None
                ...
                names.update(_PLUGIN_HOOK_SCRIPT_RE.findall(command))
    return names, errors
```

`event` appears only inside the error strings for malformed shapes. The parity
check that consumes it, `goc/engine.py:1594-1604`, is a two-way set difference
over those names:

```python
        for name in sorted(shipped - registered):
            ...
        for name in sorted(registered - shipped):
```

So "every shipped script is registered somewhere, and every registration names
a shipped script" is enforced; "this script is bound to the event it is written
for" is not. `scripts/sync_plugin_assets.py` cannot cover the gap either —
`hooks.json` sits in that script's `preserve_files` set and is never compared.

`tests/test_plugin_hook_json_registration.py:38-48` registers its fixture under
synthetic `f"Event{i}"` names, which is the clearest statement that the event is
outside the contract under test.

The script half of this contract was built deliberately and closed twice:
[plugin-payload-hooks-json-never-registers-a-newly-added-hook-script](../plugin-payload-hooks-json-never-registers-a-newly-added-hook-script/)
(done) added the two-way shipped-versus-registered difference, and
[derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
(done) made the *list* derived rather than restated. Both are scoped to which
scripts exist. Neither touches which event a script is bound to — the one half
AGENTS.md says cannot be derived, and therefore the half that has to be checked
rather than generated. This card is that gap, not a re-open of either.

## Why deferred

Confirming the gap means mutating a shipped `hooks.json` and re-entering the
validator, which is a fixture-and-temp-tree exercise rather than a read. The
round's budget went to two confirmed defects. The static reading is
unambiguous, but this card claims a *missing guard*, and a missing-guard claim
is only worth its falsification run.

## Falsification recipe

1. Copy `goc/templates/hooks/*.py` and `codex-plugin/hooks/hooks.json` into a
   temp tree shaped like `REPO_ROOT`.
2. Swap the `SessionStart` and `Stop` entries in that `hooks.json` — the
   session primer now fires on `Stop`, the pattern check on `SessionStart`.
3. Call `engine.validate_plugin_hook_registration()` and
   `engine.validate_hook_registration()`.

If the invariant is guarded, at least one returns a non-empty error list. If
the gap is real, both return `[]`. Repeat with `GOC_CLAUDE_HOOKS` mutated
instead, to establish whether the vendored path is any stronger.

## Why it would matter

A mis-bound hook is silent in exactly the way the hook system is designed not
to be: `deck_session_start.py` bound to `Stop` prints the active-card reminder
after every turn instead of once at session start, and
`pattern_generalization_check.py` bound to `SessionStart` blocks nothing and
reminds nobody. Both keep exiting 0. The registries are hand-maintained
precisely because the mapping is not derivable — which is also the reason it is
the half most likely to drift, and the half nothing reads back.
