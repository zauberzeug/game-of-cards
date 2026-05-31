---
title: hook-scripts-crash-on-non-string-field-values-with-attribute-or-typeerror
summary: "The closed predecessor `hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror` added `isinstance(data, dict)` guards on the top-level stdin payload, but the hooks still trust that individual field values are strings. `deck_prompt_router.py:79` calls `.lower()` on `data.get(\"prompt\")` and `pattern_generalization_check.py:201,204` feeds `data.get(\"transcript_path\")` to `Path(...)` without an isinstance check. A harness payload like `{\"prompt\": 123}` or `{\"transcript_path\": 42}` (valid JSON, dict-shaped, documented key present, non-string value) raises `AttributeError` / `TypeError` and exits 1, polluting the agent view on every event and swallowing the hook's effect — the exact contract the predecessor card promised to restore."
status: active
stage: null
contribution: medium
created: "2026-05-31T04:26:23Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (both hooks now exit 0 cleanly on a dict payload whose `prompt` / `transcript_path` field carries a non-string value, instead of raising `AttributeError` / `TypeError`).
  - [ ] MECHANICAL: `goc/templates/hooks/deck_prompt_router.py` guards the `prompt` field with `isinstance(..., str)` before `.lower()`.
  - [ ] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` guards the `transcript_path` field with `isinstance(..., str)` before `Path(...)`.
  - [ ] PROCESS: plugin mirrors (`claude-plugin/hooks/`, `codex-plugin/hooks/`) regenerate cleanly via the pre-commit `sync-plugin-assets` hook with the same guards applied.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Hook scripts crash on non-string field values with AttributeError or TypeError

## Location

- `goc/templates/hooks/deck_prompt_router.py:79`
- `goc/templates/hooks/pattern_generalization_check.py:201` (and `:204` via the `_had_code_mutation(transcript_path) → Path(transcript_path)` call chain)

## What's broken

The closed predecessor [`hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror`](../hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror/) added an `isinstance(data, dict)` guard immediately after `json.load(sys.stdin)` in both `deck_prompt_router.py` and `pattern_generalization_check.py` — making the hooks tolerant of a list, scalar, or `null` at the top level. The guard is now present at the entry of both `main()` functions:

`goc/templates/hooks/deck_prompt_router.py:73-79`:

```python
def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    prompt = (data.get("prompt") or "").lower()
```

But the field-value side of the contract is unguarded. `(data.get("prompt") or "").lower()` assumes `prompt`, if present, is a string. If the harness ever emits `{"prompt": 123}` (valid JSON, dict-shaped, documented key present, integer value), the chain becomes `(123 or "").lower()` → `123.lower()` → `AttributeError: 'int' object has no attribute 'lower'`.

`goc/templates/hooks/pattern_generalization_check.py:200-205`:

```python
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return 0

    if _had_code_mutation(transcript_path):
        ...
```

The truthiness guard `if not transcript_path: return 0` rejects `""`, `None`, `0`, and `[]`, but lets a non-string truthy value (e.g. `42`) pass through to `_had_code_mutation`, which calls `Path(transcript_path)` on it. `pathlib.Path.__init__` raises `TypeError` for any non-`str`/`os.PathLike` argument.

The fix shape is the same per-field `isinstance(..., str)` discipline the predecessor card applied at the dict level, one layer deeper.

## Empirical evidence

```
$ echo '{"prompt": 123}' | python3 goc/templates/hooks/deck_prompt_router.py
Traceback (most recent call last):
  File ".../goc/templates/hooks/deck_prompt_router.py", line 93, in <module>
    raise SystemExit(main())
  File ".../goc/templates/hooks/deck_prompt_router.py", line 79, in main
    prompt = (data.get("prompt") or "").lower()
AttributeError: 'int' object has no attribute 'lower'
rc=1

$ echo '{"transcript_path": 123}' | python3 goc/templates/hooks/pattern_generalization_check.py
Traceback (most recent call last):
  File ".../goc/templates/hooks/pattern_generalization_check.py", line 213, in <module>
    raise SystemExit(main())
  File ".../goc/templates/hooks/pattern_generalization_check.py", line 205, in main
    if _had_code_mutation(transcript_path):
  File ".../goc/templates/hooks/pattern_generalization_check.py", line 148, in _had_code_mutation
    path = Path(transcript_path)
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'int'
rc=1
```

## Why it matters

The reachability path is identical to the closed predecessor's: any Claude Code or Codex harness version (current or future) that emits a payload with a non-string `prompt` or `transcript_path` field triggers a raw traceback on every `UserPromptSubmit` / `Stop` event, pollutes the agent view, and silently swallows the hook's intended effect. The predecessor's closure note explicitly framed the contract as *"return 0 silently on any malformed input shape, including future harness changes"*; the field-level case violates that contract just as surely as the top-level non-dict case did.

This is a true sibling defect — same family ("hook trusts stdin shape too much"), same fix discipline (per-`isinstance` guard with silent `return 0`), one layer deeper into the payload.

## Fix

Two single-line `isinstance` guards mirroring the predecessor's pattern:

`goc/templates/hooks/deck_prompt_router.py`:

```python
    if not isinstance(data, dict):
        return 0
    prompt_raw = data.get("prompt")
    if not isinstance(prompt_raw, str):
        return 0
    prompt = prompt_raw.lower()
```

`goc/templates/hooks/pattern_generalization_check.py`:

```python
    transcript_path = data.get("transcript_path", "")
    if not isinstance(transcript_path, str) or not transcript_path:
        return 0
```

Plugin mirrors under `claude-plugin/hooks/` and `codex-plugin/hooks/` regenerate from the templates via `scripts/sync_plugin_assets.py` (auto-staged by the `sync-plugin-assets` pre-commit hook).
