## 2026-05-26 — EMPIRICAL verdict: order-dependence TRUE, but UNREACHABLE → disproved

Ran the falsification recipe.

**Order-dependence (the code claim): CONFIRMED.** Built the A/B/X cyclic
deck (`A advances [B]`, `B advances [A]`, both `high`; `X advances [A]`,
`low`) and called `compute_values` twice:

- `cards=[A,B,X]` → A=19.710, B=15.300
- `cards=[B,A,X]` → A=15.300, B=19.710

So `compute_values` does NOT deliver the order-independent per-card-rank
fallback (both 9.0) the docstring promised. The hunter's prediction was
exactly right.

**Reachability: UNREACHABLE in any deck that passes `goc validate`.**
Both guards verified empirically:

- `detect_advance_cycles` flags the A↔B loop (`['A: advanced_by: cycle
  detected through B → A', ...]`) and its result appends to `errors`,
  which gates the exit code at `engine.py:2381-2383` + `2393-2394`
  (`if errors: sys.exit(1)`). A cycle is a hard validation ERROR.
- `_would_create_advance_cycle(acyclic A→B deck, "A", "B")` returns
  `True` — i.e. `goc advance A --by B` (the edge that would close the
  loop) is refused at `engine.py:3740`.

So the order-dependent branch (`if title in in_progress`) is pure
defensive code that only executes on a deck already failing validation.
User-facing priority math is never corrupted for a valid deck.

**Resolution (MECHANICAL branch of the DoD):** corrected the docstring
at `engine.py` `compute_values` to stop claiming a per-card-rank
fallback the code does not deliver, and to state plainly that the
in-progress guard is unreachable defensive code on any valid deck.
Disproved/closed — the defect as a live priority-corruption bug does
not exist; the only real issue was the docstring overclaim, now fixed.
