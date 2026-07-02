---
title: load-deck-config-crashes-on-non-mapping-config-yaml
status: done
stage: null
contribution: medium
created: "2026-07-02T02:19:55Z"
closed_at: "2026-07-02T02:25:03Z"
human_gate: none
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, api-contract]
summary: |
  A non-mapping `.game-of-cards/config.yaml` (a bare YAML list or scalar)
  parses to a Python list/str that `load_deck_config()` returns unguarded, so
  every caller's `.get()` raises AttributeError — crashing every mutating verb
  after the README write but before the auto-commit, leaving the card mutated
  on disk but never committed. Same bug class as the just-guarded
  canonical-tags loader; `load_deck_config` is the loader that never got the
  isinstance guard.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (a bare-list and a scalar config.yaml no longer crash `goc status`)
  - [x] TDD: load_deck_config() returns {} (not the list/str) when config.yaml parses to a non-mapping
  - [x] MECHANICAL: the isinstance guard mirrors the two existing siblings (`_resolve_deck_root`, `_load_consuming_repo_tags`)
  - [x] PROCESS: regression test added to tests/ and the full suite stays green
worker: {who: "claude[bot]", where: main}
---

# load-deck-config-crashes-on-non-mapping-config-yaml

## Location

`goc/engine.py:4648-4653` — `load_deck_config()`.

## What's broken

`load_deck_config()` returns whatever `yaml.safe_load` produced, guarding
only the falsy case:

```python
def load_deck_config() -> dict:
    if GAME_OF_CARDS_CONFIG_FILE.exists():
        return yaml.safe_load(GAME_OF_CARDS_CONFIG_FILE.read_text()) or {}
    if LEGACY_DECK_CONFIG_FILE.exists():
        return yaml.safe_load(LEGACY_DECK_CONFIG_FILE.read_text()) or {}
    return {"layer_2_project_dod": [], "layer_3_goc_dod": []}
```

A non-mapping `config.yaml` — a bare YAML list, or a scalar — parses to a
Python `list`/`str`. The `... or {}` keeps the *truthy* non-dict. Every
caller then calls `.get()` on it with no guard:

- `goc/engine.py:4463` (`auto_commit_enabled`): `workflow = config.get("workflow") or {}`
- `goc/engine.py:4483`, `4537` (`_enforce_closure_on_integration_or_exit`)
- `goc/engine.py:4667` (`get_skills_source`): `value = load_deck_config().get("skills_source")`
- `goc/engine.py:4963` (`_cmd_attest`)

`auto_commit_enabled()` runs on essentially **every mutating verb**
(`status`, `done`, `wait`, `advance`, `unadvance`, `decide`, `publish`,
`new`, `move`) whenever the deck is git-tracked. `get_skills_source()` runs
in `goc validate` and `goc upgrade`.

This is an unguarded sibling of the bug class the maintainers just fixed for
the canonical-tags loader (commit `e1984e1`). That fix, at
`goc/engine.py:647-652`, spells out exactly why the guard belongs on the
block itself, not just its value:

```python
        # Guard the block itself, not just its value: `_FENCED_YAML`
        # matches every ```yaml block in the file, and a non-mapping
        # block (a bare list, a scalar) has no `.get` — calling it would
        # crash every goc command via `load_schema()` at import time.
        if not isinstance(block, dict):
            continue
```

`_resolve_deck_root` (`engine.py:88-93`) is likewise guarded (its
`cfg.get(...)` is wrapped in try/except). `load_deck_config` is the one
loader that never got the guard.

## Empirical evidence

```
$ printf -- '- a\n- b\n' > .game-of-cards/config.yaml   # bare list
$ goc status sample-card open
sample-card: active → open
Traceback (most recent call last):
  ...
  File ".../goc/engine.py", line 4463, in auto_commit_enabled
    workflow = config.get("workflow") or {}
               ^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'
# exit code 1
```

The README write lands first (`sample-card: active → open` prints), then the
command dies with an uncaught traceback — so the card is mutated on disk but
the auto-commit never runs. A scalar config throws an uncaught
`yaml_lite.ParseError` from the load itself.

## Why it matters

Reachability: `.game-of-cards/config.yaml` is a **user-owned / evolving**
file per the ownership model (AGENTS.md). A human hand-edit that accidentally
produces a top-level list (e.g. writing the DoD-check list at the top level
instead of under a `layer_2_project_dod:` key) is enough to trigger it. From
then on, *every* mutating `goc` verb crashes after partially mutating the
target card, and `goc validate` / `goc upgrade` crash outright — with a raw
Python traceback rather than a clean diagnostic. The partial-mutation window
(README flipped, commit skipped) is the sharp edge: parallel agents rely on
the auto-commit to publish claim/progress state, so a silent half-write
desyncs the shared deck.

## Fix

Guard the parsed result in `load_deck_config`, mirroring the two existing
siblings — coerce any non-mapping (including the `ParseError` path) to `{}`:

```python
def load_deck_config() -> dict:
    for path in (GAME_OF_CARDS_CONFIG_FILE, LEGACY_DECK_CONFIG_FILE):
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text())
            except Exception:
                return {}
            return data if isinstance(data, dict) else {}
    return {"layer_2_project_dod": [], "layer_3_goc_dod": []}
```

This keeps the existing "absent → default DoD scaffold" behavior while
treating a malformed config as empty, exactly as the guarded loaders do. Do
NOT swallow the error silently at the call sites — the single loader is the
right chokepoint, matching the sibling design.
