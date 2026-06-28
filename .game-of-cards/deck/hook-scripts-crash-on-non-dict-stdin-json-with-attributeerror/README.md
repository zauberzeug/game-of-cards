---
title: hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror
summary: "Two of the three Claude/Codex lifecycle hooks shipped under `goc/templates/hooks/` parse stdin JSON and then call `.get(...)` on the result without an `isinstance(data, dict)` guard. The sibling `deck_session_start.py:163` already guards correctly, so the asymmetry is right there in the same directory. A harness payload that parses to a list, scalar, or `null` crashes `deck_prompt_router.py` and `pattern_generalization_check.py` with a raw `AttributeError` instead of returning 0 silently."
status: done
stage: null
contribution: medium
created: "2026-05-30T17:31:31Z"
closed_at: "2026-05-30T17:33:51Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero (both hooks now exit 0 cleanly on a non-dict stdin payload — list, scalar, `null` — instead of raising `AttributeError`).
  - [x] MECHANICAL: `goc/templates/hooks/deck_prompt_router.py` adds an `isinstance(data, dict)` guard after `json.load(sys.stdin)` mirroring the existing pattern at `deck_session_start.py:163`.
  - [x] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` adds the same guard before its first `data.get(...)` call.
  - [x] PROCESS: plugin mirrors (`claude-plugin/hooks/`, `codex-plugin/hooks/`) regenerate cleanly via the pre-commit `sync-plugin-assets` hook with the same guards applied.
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Hook scripts crash on non-dict stdin JSON with AttributeError

## Location

- `goc/templates/hooks/deck_prompt_router.py:77`
- `goc/templates/hooks/pattern_generalization_check.py:191` (and `:194`, `:198`)

## What's broken

Three lifecycle hooks ship under `goc/templates/hooks/`. They each
read a JSON payload from stdin (the Claude Code / Codex harness
contract for `UserPromptSubmit`, `SessionStart`, `Stop`). Two of the
three call `.get(...)` on the parsed result without first checking
that it is a dict.

`deck_prompt_router.py:72-77`:

```python
def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = (data.get("prompt") or "").lower()
```

`pattern_generalization_check.py:185-198`:

```python
def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    ...
    transcript_path = data.get("transcript_path", "")
```

The sibling `deck_session_start.py:158-169` already does the right
thing and is the existing pattern in the same directory:

```python
def _project_dir_from_hook_input() -> str:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if isinstance(data, dict) and data.get("cwd"):
        return str(data["cwd"])
```

When the parsed payload is a list, a scalar, or `null` — all valid
JSON shapes — the two unguarded hooks raise
`AttributeError: 'list' object has no attribute 'get'` and exit 1
instead of returning 0 cleanly. For the `Stop` hook
(`pattern_generalization_check.py`) the crash exit code (1) is not
the documented blocking-2 path either, so it pollutes stderr without
delivering the intended generalization reminder.

## Empirical evidence

```
$ echo '[1,2,3]' | python3 goc/templates/hooks/deck_prompt_router.py
Traceback (most recent call last):
  File "deck_prompt_router.py", line 91, in <module>
    raise SystemExit(main())
  File "deck_prompt_router.py", line 77, in main
    prompt = (data.get("prompt") or "").lower()
AttributeError: 'list' object has no attribute 'get'
exit: 1

$ echo '[1,2,3]' | python3 goc/templates/hooks/pattern_generalization_check.py
Traceback (most recent call last):
  File "pattern_generalization_check.py", line 210, in <module>
    raise SystemExit(main())
  File "pattern_generalization_check.py", line 191, in main
    if data.get("stop_hook_active"):
AttributeError: 'list' object has no attribute 'get'
exit: 1
```

`deck_session_start.py` is unaffected — its `isinstance(data, dict)`
guard short-circuits to the env-var fallback path.

## Why it matters

Reachability: the Claude Code / Codex harnesses *should* always emit
a JSON object payload on every hook event, but "should" is not
"will". The same family of crashes has already been documented and
fixed twice at user-editable-config loaders — see
[`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/)
and
[`frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror`](../frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror/),
plus the open meta-card
[`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/).
This card is the hook-payload sibling family — distinct from the
loader-callsite family because the payload comes from the harness,
not a user-editable config file, so the fix is the local guard not
a shared loader helper.

A crash inside a `UserPromptSubmit` or `Stop` hook does not destroy
user data, but it produces a noisy traceback in the agent's view on
every event and silently swallows the hook's intended effect (the
deck-first reminder; the generalization-prompt heuristic). The fix
is one line per file, mirroring the existing sibling pattern.

## Fix

For each of the two hooks, add a `not isinstance(data, dict)` guard
immediately after the try/except around `json.load(sys.stdin)`:

```python
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
```

This matches the recovery behavior of the existing JSONDecodeError
branch: malformed payload → return 0 silently and let the harness
continue.

Then re-run `python scripts/sync_plugin_assets.py` (or let the
pre-commit `sync-plugin-assets` hook do it) so the `claude-plugin/`
and `codex-plugin/` mirrors pick up the fix.
