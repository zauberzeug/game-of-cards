
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

## 2026-09-07 — refine-deck: defunct cite repaired by hand from the prior pass's note

The 2026-08-31 entry above recorded that the `_would_create_advance_cycle`
cite (`:1349`) was defunct, that its anchor text had been refactored into
`advances = card.frontmatter.get("advances") or []`, and that the function
now sits at `goc/engine.py:2136` with its `advances` walk at `:2154`. That
located the cite; the mechanical pass could not apply it, because the recipe
only rewrites a number when the *verbatim* anchor line relocates uniquely.

Re-verified against HEAD (`def _would_create_advance_cycle` at line 2136,
`advances = card.frontmatter.get("advances") or []` at 2154) and applied the
repair to both the summary and the Location block, including the quoted
snippet, which was still the pre-refactor form. `detect_advance_cycles`'s
`:~2126` cite was checked and is current.

The divergence itself is unchanged and the decision is still parked: the
gating validator walks `advanced_by`, the live guard walks `advances`. No
`reproduce.py` this round — the fixture needs a half-edged deck that
`goc validate` rejects and no goc verb can produce, which is part of what
the parked decision has to weigh.
