
## 2026-08-31 — refine-deck: stale park re-checked, kept

96 days parked. Re-read against HEAD rather than resetting the clock blind:
the divergence is unchanged. `detect_advance_cycles` still walks
`advanced_by` (`goc/engine.py:2126`) while `_would_create_advance_cycle`
still walks `advances` (`goc/engine.py:2154`).

Cite state after this pass: the `detect_advance_cycles` cite was repaired to
`:~2126`. The `_would_create_advance_cycle` cite still reads `:1349` and is
defunct — its anchor line (`for a in card.frontmatter.get("advances") or []:`)
was refactored into `advances = card.frontmatter.get("advances") or []` and no
longer exists verbatim, so the mechanical pass declined it rather than guess.
The function is at `goc/engine.py:2136` and its `advances` walk at `:2154`;
whoever takes the decision should correct the cite by hand.

No `reproduce.py` built this round. The recipe needs a deliberately
half-edged deck, which `goc validate` rejects and no goc verb can produce —
so the fixture has to be hand-written frontmatter, and the honest scope of
the resulting evidence (a state the tool refuses to create) is itself part
of what the parked decision has to weigh. That is more than a hygiene pass
should settle unilaterally.
