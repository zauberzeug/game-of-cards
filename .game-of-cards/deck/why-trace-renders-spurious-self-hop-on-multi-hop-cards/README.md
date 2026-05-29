---
title: why-trace-renders-spurious-self-hop-on-multi-hop-cards
summary: "The `-v` WHY column appends a spurious `→ self (?)` hop to every card whose value trace passes through at least one descendant. `_format_why` only suppresses the exact leaf path `[\"self\"]`, but `compute_values` drags the `\"self\"` sentinel into the tail of every longer `top_path`, so the loop renders it as an unknown-contribution slug."
status: done
stage: null
contribution: medium
created: "2026-05-27T03:45:33Z"
closed_at: "2026-05-27T03:51:32Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a multi-hop `top_path` ending in the `"self"` sentinel renders WITHOUT a trailing `→ self (?)`, and the leaf/empty cases still render `""`.
  - [x] TDD: `_format_why(["B", "C", "self"], {...})` returns `"→ B (low) → C (low)"` (no `self` hop); `_format_why(["self"], {})` still returns `""`; the `["cycle"]` case still returns `"(cycle)"`.
  - [x] EMPIRICAL: `uv run goc -v` no longer prints `→ self (?)` on any card (verify against the active/open queue, e.g. `support-external-game-of-cards-state-location` and `remove-blocked-from-status-enum-and-migrate-existing-cards`).
  - [x] MECHANICAL: `uv run goc validate` clean; plugin-asset sync `--check` green (engine mirrors re-synced if `engine.py` changed under the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# WHY trace renders a spurious `→ self (?)` hop on every multi-hop card

The verbose (`-v`) WHY column on the queue/board appends a bogus
`→ self (?)` to the priority-propagation trace of any card whose value
flows through at least one live descendant. The `self` sentinel is an
internal terminator, not a real card, so it renders with an
unknown-contribution `(?)`.

## Location

- `goc/engine.py:1853` — leaf cards terminate their `top_path` with the
  literal sentinel `["self"]`.
- `goc/engine.py:1848` — a parent *prepends* its descendant slug:
  `best = (d_value, [dest, *d_path])`. This drags the `"self"` sentinel
  into the tail of every multi-hop path (e.g. `["B", "C", "self"]`).
- `goc/engine.py:2032-2043` — `_format_why` only special-cases the
  *exact* leaf path `path == ["self"]`; a longer path that merely *ends*
  in `"self"` falls through to the slug loop.

## What's broken

`compute_values` builds the trace bottom-up. A leaf returns:

```python
result = (own, ["self"])          # engine.py:1853
```

Each ancestor prepends its own descendant slug:

```python
best = (d_value, [dest, *d_path])  # engine.py:1848
```

So a two-hop chain `A → B → C(leaf)` gives `A` the path
`["B", "C", "self"]` — the sentinel rides along in the tail.

`_format_why` guards only the bare leaf:

```python
def _format_why(path: list[str], by_title: dict[str, Card]) -> str:
    """Format the GRPW propagation trace: 'self' → '' (omit); chain → '→ A (high) → B (med)'."""
    if not path or path == ["self"]:      # engine.py:2034 — exact match only
        return ""
    if path == ["cycle"]:
        return "(cycle)"
    parts = []
    for slug in path:                     # engine.py:2039
        c = by_title.get(slug)
        contrib = c.contribution if c else "?"   # by_title.get("self") is None → "?"
        parts.append(f"→ {slug} ({contrib})")
    return " ".join(parts)
```

For `["B", "C", "self"]` the loop reaches `slug == "self"`,
`by_title.get("self")` is `None`, so it emits `→ self (?)`. The
docstring's own contract — *"chain → '→ A (high) → B (med)'"* — names no
`self` hop; the rendered output contradicts it.

## Empirical evidence

This bug is **live in the current deck**. `uv run goc -v` prints, on the
active queue:

```
support-external-game-of-cards-state-location
    why: → ship-game-of-cards-as-cross-agent-cli (high) → self (?)

remove-blocked-from-status-enum-and-migrate-existing-cards
    why: → blocked-status-conflates-dependency-external-wait-and-deferral (medium) → self (?)
```

Direct unit reproduction (`reproduce.py`):

```
A 3-hop: '→ B (low) → C (low) → self (?)'   <- BUG: trailing self hop
B 2-hop: '→ C (low) → self (?)'             <- BUG: trailing self hop
leaf   : ''                                  <- correct
```

Expected (correct) output:

```
A 3-hop: '→ B (low) → C (low)'
B 2-hop: '→ C (low)'
leaf   : ''
```

## Why it matters

The WHY column is a documented display contract (`_format_why`'s own
docstring) and the primary explanation an operator reads to understand
*why* a card carries the priority it does. Appending `→ self (?)` to
essentially every non-leaf card makes the trace read as if there is a
mysterious unknown-contribution card named `self` at the end of every
chain — noise that undermines trust in the priority math and clutters
the queue/board output a human scans during triage.

## Fix

Two equivalent approaches; either satisfies the DoD. Prefer the first
(localized, no change to the value-graph data shape):

1. In `_format_why`, strip a trailing `"self"` sentinel before the slug
   loop:

   ```python
   if path and path[-1] == "self":
       path = path[:-1]
   if not path:
       return ""
   ```

   (placed after the `["cycle"]` guard, before building `parts`).

2. Alternatively, in `compute_values`, do not embed the sentinel into
   ancestor paths — keep the leaf path empty (`result = (own, [])`) and
   adjust the leaf/empty handling in `_format_why` accordingly. This
   changes the cached `top_path` shape, so audit any other consumer of
   `top_path` first.

Approach 1 is the minimal, contained fix and is recommended.
