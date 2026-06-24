---
title: render-json-value-path-leaks-self-and-cycle-trace-sentinels
status: done
stage: null
contribution: medium
created: "2026-06-24T19:20:44Z"
closed_at: "2026-06-24T19:25:04Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a multi-hop card's `value_path` in `goc --json` contains only real card slugs (no trailing `"self"`), a leaf's `value_path` is `[]`, and the cyclic-deck case drops the `"cycle"` sentinel.
  - [x] TDD: `render_json` and `_format_why` derive the slug chain from one shared helper so the machine and human surfaces cannot drift apart again.
  - [x] MECHANICAL: `uv run goc validate` clean; plugin-asset sync `--check` green (engine mirrors re-synced).
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes.
worker: {who: "claude[bot]", where: main}
---

# `render_json` leaks the `"self"` / `"cycle"` value-trace sentinels into `value_path`

The machine-readable `value_path` field emitted by `goc --json` carries
internal terminator sentinels (`"self"`, `"cycle"`) as if they were card
titles. The human-facing `-v` WHY column already strips them; the JSON
surface does not, so the two presentations of the same chain disagree.

## Location

- `goc/engine.py:2864` — the non-slim `render_json` record builder emits
  the raw path:

  ```python
  "value_path": values.get(t.title, (0.0, []))[1],
  ```

- `goc/engine.py:2419` — `compute_values` terminates every leaf path with
  the literal sentinel `["self"]`, and `engine.py:2414` prepends each
  descendant slug (`best = (d_value, [dest, *d_path])`), so `"self"` rides
  in the tail of every multi-hop path. A validate-failing cyclic deck does
  the same with `["cycle"]` (`engine.py:2375`).

- `goc/engine.py:2705-2708` — `_format_why` (the `-v` WHY column) strips the
  trailing `"self"` / `"cycle"` sentinel before rendering, which is why the
  human surface is correct and the JSON surface is not.

## What's broken

`"self"` and `"cycle"` are documented internal terminators (see the
`compute_values` docstring, `engine.py:2341-2358`), not card titles. A
consumer reading `value_path` expects a list of the card slugs on the
argmax value chain. Instead it gets the sentinel appended to the tail:
a leaf reports `["self"]` instead of `[]`, and every ancestor reports
`[..., "self"]`.

## Empirical evidence

Pre-fix, `value_path` leaked the `"self"` sentinel; post-fix it carries
only real card slugs, matching the WHY column. After the fix
`reproduce.py` exits zero:

```
$ uv run python .game-of-cards/deck/render-json-value-path-leaks-self-and-cycle-trace-sentinels/reproduce.py
value_path leak in render_json:
  root-card  -> ['mid-card', 'leaf-card']
  mid-card   -> ['leaf-card']
  leaf-card  -> []
WHY column (-v, already correct) for the same chain:
  root-card  -> → mid-card (medium) → leaf-card (high)
  leaf-card  -> (empty)
OK: value_path carries only real card slugs (no sentinel leak).
```

## Why it matters

`goc --json` is the documented machine surface for external consumers
(trackers, dashboards, the SaaS-sync work). The reachability path is
direct: `render_json` is reached by every `goc --json` / `goc --board
--json` invocation, and the sentinel rides in for every card that has at
least one live descendant — i.e. every non-leaf card in any deck with an
`advances` chain (the common case). A consumer that joins `value_path`
slugs against card titles silently fails to resolve `"self"` / `"cycle"`,
or worse treats them as a phantom card.

The two closed sibling cards
[why-trace-renders-spurious-self-hop-on-multi-hop-cards](../why-trace-renders-spurious-self-hop-on-multi-hop-cards/)
and
[why-trace-renders-spurious-cycle-hop-on-cyclic-deck](../why-trace-renders-spurious-cycle-hop-on-cyclic-deck/)
fixed this exact sentinel leak, but only in `_format_why` (the table
`-v` path). They pinned the contract — "the chain is a list of real card
slugs; the internal terminator is stripped" — without touching the JSON
surface. This card extends that already-decided contract to `render_json`.

## Fix

Factor the trailing-sentinel strip into one shared helper so both render
surfaces agree by construction (and cannot drift apart a third time):

```python
def _value_path_slugs(path: list[str]) -> list[str]:
    """The argmax descendant chain as real card slugs (internal
    `"self"` / `"cycle"` terminator stripped)."""
    if path and path[-1] in ("self", "cycle"):
        return path[:-1]
    return path
```

`render_json` emits `_value_path_slugs(values.get(...)[1])`; `_format_why`
routes its existing trailing-strip through the same helper (preserving its
`(cycle)` suffix behaviour). Gate is `none`: the correct behaviour is
fully determined by the two closed WHY-trace cards — the machine surface
must agree with the human one.
