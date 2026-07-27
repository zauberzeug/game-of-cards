---
title: deck-count-messages-print-1-cards-instead-of-1-card
summary: "Six user-facing count messages in goc/engine.py hardcode the plural noun, so a one-card result reads 'Quality pass over 1 cards' and 'Waiting on you (gate != none) - 1 cards'. The same file already carries two working conventions for this — the plural-aware ternary in render_active_notice and the 'card(s)' form used by migrate and migrate-list-style — so the defect is an inconsistency inside one module, not a missing capability."
status: active
stage: null
contribution: low
created: "2026-07-27T01:15:46Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no `{len(...)} cards` interpolation with a hardcoded plural noun remains in `goc/engine.py`, and a one-card scratch deck prints no `1 cards` line.
  - [ ] MECHANICAL: all seven sites listed below use one of the two conventions the module already ships (`card(s)`, or the `noun = "card" if … else "cards"` form from `render_active_notice`) — pick one and apply it uniformly rather than mixing a third.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Count messages print "1 cards" instead of "1 card"

## Location

Seven `{len(...)} cards` interpolations in `goc/engine.py` hardcode the
plural noun:

| Line | Message | Reachable with count 1? |
|---|---|---|
| 4188 | `Quality pass over {len(cards)} cards (status={status_flag}):` | yes |
| 4191 | `Title antipatterns ({len(title_hits)} cards):` | yes |
| 4201 | `Missing summary ({len(missing_summary)} cards):` | yes |
| 4214 | `Layer-2 (Sonnet pass): auditing {len(sample)} cards via …` | yes |
| 4241 | `Sonnet pass: {len(verdicts)} cards audited, …` | yes |
| 6187 | `## Waiting on you (gate ≠ none) — {len(payload)} cards` | yes |
| 4397 | `Bundled close: {len(plan)} cards.` | **no** — `--bundle` refuses fewer than 2 titles, so this one can never render "1 cards" |

Six are live defects; 4397 is listed because it belongs to the same sweep
and would drift back into a defect if the two-title floor ever moves.

## What's broken

The engine renders a hardcoded plural regardless of count, so every
one-result view reads ungrammatically. `goc/engine.py:4188`:

```python
    print(f"\nQuality pass over {len(cards)} cards (status={status_flag}):\n")
```

and `goc/engine.py:6187`:

```python
    lines = [f"## Waiting on you (gate ≠ none) — {len(payload)} cards", ""]
```

This is an inconsistency *inside one module*, not a missing capability —
`goc/engine.py` already ships two working conventions for the same problem.
`render_active_notice` at `goc/engine.py:3390`:

```python
    noun = "card" if len(active) == 1 else "cards"
    return (
        f"ACTIVE: {len(active)} claimed {noun} outside this open queue: {shown}. "
```

and the `migrate` / `migrate-list-style` paths at `:6340`, `:6390`, `:6395`:

```python
        print(f"Rewrote {len(changed)} card(s):")
```

So the deck's own output is internally inconsistent: `goc` announces
"1 claimed card", while `goc triage` on the same deck announces
"1 cards".

## Empirical evidence

`reproduce.py` builds a scratch deck holding exactly one card, runs the two
reachable surfaces, then statically classifies every count-interpolated card
noun in the engine:

```
$ uv run python .game-of-cards/deck/deck-count-messages-print-1-cards-instead-of-1-card/reproduce.py
live output on a deck holding exactly one card:
  $ goc quality-pass --no-llm
    Quality pass over 1 cards (status=open):
  $ goc triage
    ## Waiting on you (gate ≠ none) — 1 cards

plural-safe `card(s)` sites: 3
  goc/engine.py:6340  prompt = f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"
  goc/engine.py:6390  print(f"Would rewrite {len(changed)} card(s):")
  goc/engine.py:6395  print(f"Rewrote {len(changed)} card(s):")
plural-safe ternary sites: 1 (lines [3390])

plural-UNSAFE hardcoded `cards` sites: 7
  goc/engine.py:4188  print(f"\nQuality pass over {len(cards)} cards (status={status_flag}):\n")
  goc/engine.py:4191  print(f"Title antipatterns ({len(title_hits)} cards):")
  goc/engine.py:4201  print(f"Missing summary ({len(missing_summary)} cards):")
  goc/engine.py:4214  print(f"Layer-2 (Sonnet pass): auditing {len(sample)} cards via `claude --model sonnet -
  goc/engine.py:4241  print(f"\nSonnet pass: {len(verdicts)} cards audited, {rewrite_count} with proposed rewr
  goc/engine.py:4397  print(f"\nBundled close: {len(plan)} cards.")
  goc/engine.py:6187  lines = [f"## Waiting on you (gate ≠ none) — {len(payload)} cards", ""]

FAIL: 7 count message(s) hardcode the plural noun while the same module already ships 3 `card(s)` sites and 1 plural-aware ternary site(s)
```

## Why it matters

Small, but it lands on the two surfaces a human reads most when the deck is
nearly drained — `goc triage` (the human's parked-card handoff) and
`goc quality-pass` (the hygiene report). A one-card deck is the *normal*
end state of a well-drained queue, so this is the wording the tool shows
exactly when the operator is paying attention.

Filed as a sweep rather than a point fix: seven sites is past the threshold
where fixing one in passing just leaves six behind. The fix is mechanical and
gate-free — the module has already made this choice twice, so the card is a
sweep to one of the existing conventions, not a new design.

## Fix

Pick one of the two conventions already present and apply it to all seven
sites. `card(s)` is the smaller edit and already carries three sites;
the `noun = "card" if … else "cards"` form reads better in prose sentences
like `Quality pass over 1 card` and matches `render_active_notice`, which is
the closest neighbour in intent (both are queue-summary banners). Whichever
is chosen, do not introduce a third form.
