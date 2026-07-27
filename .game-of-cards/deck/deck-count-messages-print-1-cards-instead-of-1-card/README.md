---
title: deck-count-messages-print-1-cards-instead-of-1-card
summary: "Six user-facing count messages in goc/engine.py hardcode the plural noun, so a one-card result reads 'Quality pass over 1 cards' and 'Waiting on you (gate != none) - 1 cards'. The same file already carries two working conventions for this — the plural-aware ternary in render_active_notice and the 'card(s)' form used by migrate and migrate-list-style — so the defect is an inconsistency inside one module, not a missing capability."
status: done
stage: null
contribution: low
created: "2026-07-27T01:15:46Z"
closed_at: "2026-07-27T01:27:11Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no `{len(...)} cards` interpolation with a hardcoded plural noun remains in `goc/engine.py`, and a one-card scratch deck prints no `1 cards` line.
  - [x] MECHANICAL: all seven sites listed below use one of the two conventions the module already ships (`card(s)`, or the `noun = "card" if … else "cards"` form from `render_active_notice`) — pick one and apply it uniformly rather than mixing a third.
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
  - [x] GUARD: the swept convention is enforced by CI, not only by this card's `reproduce.py` — `tests/test_count_message_pluralization.py` fails on any reintroduced hardcoded-plural count banner. (Added during closure: `reproduce.py` lives in the deck and CI never runs it, so without this the sweep had no guard against drifting back one site at a time.)
worker: {who: "claude[bot]", where: main}
---

# Count messages print "1 cards" instead of "1 card"

## Location

Seven `{len(...)} cards` interpolations in `goc/engine.py` hardcoded the
plural noun. All seven now route through `_cards_noun()`:

| Line (pre → post) | Message | Reachable with count 1? |
|---|---|---|
| 4188 → 4199 | `Quality pass over {len(cards)} cards (status={status_flag}):` | yes |
| 4191 → 4202 | `Title antipatterns ({len(title_hits)} cards):` | yes |
| 4201 → 4212 | `Missing summary ({len(missing_summary)} cards):` | yes |
| 4214 → 4225 | `Layer-2 (Sonnet pass): auditing {len(sample)} cards via …` | yes |
| 4241 → 4252 | `Sonnet pass: {len(verdicts)} cards audited, …` | yes |
| 6187 → 6198 | `## Waiting on you (gate ≠ none) — {len(payload)} cards` | yes |
| 4397 → 4408 | `Bundled close: {len(plan)} cards.` | **no** — `--bundle` refuses fewer than 2 titles, so this one can never render "1 cards" |

Six were live defects; 4397 was swept because it belongs to the same family
and would drift back into a defect if the two-title floor ever moves. Post-fix
line numbers are +11 from the pre-fix ones — the `_cards_noun` definition sits
above all seven.

## What was broken

The engine rendered a hardcoded plural regardless of count, so every
one-result view read ungrammatically — `goc` announced "1 claimed card"
while `goc triage` on the same deck announced "1 cards".

That was an inconsistency *inside one module*, not a missing capability:
`goc/engine.py` already shipped two working conventions for the same
problem — the plural-aware ternary in `render_active_notice`, and the
`card(s)` form in the `migrate` / `migrate-list-style` paths — and the
seven count banners used neither.

## Empirical evidence

`reproduce.py` builds a scratch deck holding exactly one card, runs the two
reachable surfaces, then statically classifies every count-interpolated card
noun in the engine. Before the fix it reported 7 plural-unsafe sites and both
surfaces printing `1 cards`. After:

```
$ uv run python .game-of-cards/deck/deck-count-messages-print-1-cards-instead-of-1-card/reproduce.py
live output on a deck holding exactly one card:
  (none)

plural-safe `card(s)` sites: 3
  goc/engine.py:6351  prompt = f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"
  goc/engine.py:6401  print(f"Would rewrite {len(changed)} card(s):")
  goc/engine.py:6406  print(f"Rewrote {len(changed)} card(s):")
plural-safe ternary sites: 9 (lines [1200, 3401, 4199, 4202, 4212, 4225, 4252, 4408, 6198])

plural-UNSAFE hardcoded `cards` sites: 0

PASS: every count message in goc/engine.py pluralizes correctly
```

The nine plural-safe ternary sites are the one `_cards_noun` definition plus
its eight call sites (the seven swept banners and `render_active_notice`).
`reproduce.py`'s `SAFE_TERNARY` classifier was widened to recognize the
factored helper alongside the inline ternary — the FAIL predicate (the
plural-unsafe count) is unchanged, so the guard was not weakened to pass.

Live output on the real deck confirms plural counts still read correctly:
`## Waiting on you (gate ≠ none) — 166 cards`, `Quality pass over 169 cards`.

## Why it matters

Small, but it landed on the two surfaces a human reads most when the deck is
nearly drained — `goc triage` (the human's parked-card handoff) and
`goc quality-pass` (the hygiene report). A one-card deck is the *normal*
end state of a well-drained queue, so this was the wording the tool showed
exactly when the operator was paying attention.

Filed as a sweep rather than a point fix: seven sites is past the threshold
where fixing one in passing just leaves six behind. The fix was mechanical and
gate-free — the module had already made this choice twice, so the card was a
sweep to one of the existing conventions, not a new design.

## Fix as applied

The ternary convention won over `card(s)`: most of the seven banners are prose
sentences where `Quality pass over 1 card` reads correctly and
`Quality pass over 3 card(s)` reads like a hedge, and `render_active_notice` —
the closest neighbour in intent, both being queue-summary banners — already
used it.

Rather than duplicate the ternary eight times, it was factored into one
module-level helper beside `_format_elapsed` (`goc/engine.py:1200`):

```python
def _cards_noun(count: int) -> str:
    return "card" if count == 1 else "cards"
```

All seven banners now interpolate `{_cards_noun(...)}`, and
`render_active_notice` was routed through the same helper so the convention has
a single definition instead of a ninth copy. This is the named ternary
convention, not a third form — the rendered wording is byte-identical to what
`render_active_notice` produced before (`tests/test_install.py` asserts
`ACTIVE: 1 claimed card` and still passes untouched).

The three `card(s)` sites in the `migrate` / `migrate-list-style` paths were
left alone: they are already plural-safe, so touching them would have widened
the diff past the card's scope. The module therefore still carries both
accepted conventions — but no unsafe ones.

`4397` (`Bundled close:`) was swept even though `--bundle` refuses fewer than
two titles and it can never render `1 cards` today; it is now correct by
construction if that floor ever moves.

## Guard

`reproduce.py` lives under `.game-of-cards/deck/` and CI never runs it, so on
its own it proved the fix without protecting it — a future edit could
reintroduce a hardcoded plural at one site and nothing would turn red. The
closure therefore added `tests/test_count_message_pluralization.py`, which runs
in the regression suite and asserts three things: `_cards_noun` returns the
singular only for exactly 1; no `{len(...)} cards` hardcoded-plural shape
survives anywhere in `goc/engine.py` (the drift guard, modelled on the existing
static source guard in `tests/test_engine_module_singletons.py`); and a one-card
scratch deck renders `Quality pass over 1 card` and
`## Waiting on you (gate ≠ none) — 1 card` end-to-end.

The guard was verified to fail, not merely pass: reverting `Bundled close:` to
the hardcoded plural made the test fail and name that exact site, and the
revert was then undone.
