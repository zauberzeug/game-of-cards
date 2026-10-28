

## 2026-07-13 — Deck hygiene pass

Wired missing predecessor edge surfaced by the orphaned-dependency sub-check (meta-fix tagged, zero edges): `advanced_by += no-guardrail-for-canonical-epic-edge-direction` — the closed parent card whose advisory this defect lives in.


## 2026-10-28: the swapped unadvance is now refused, not a silent no-op

`goc-unadvance-claims-success-when-removing-a-non-existent-edge` closed:
`goc unadvance` now exits 2 with nothing written when neither half of the
named edge is listed, and names the reversed command when the edge runs the
other way. The warning's first verbatim command, `goc unadvance card-a --by
child-x`, therefore prints `ERROR: cannot remove child-x → card-a: no such
edge — …; the edge runs the other way (card-a → child-x) — if that is the
one to remove, run `goc unadvance child-x --by card-a`` instead of a removal
line. That is this card's corrected first step, so a reader following the
warning is now pointed at the right command, but the warning text itself is
still swapped and the second command still re-adds the bad edge (until
`goc-advance-claims-success-when-adding-an-already-existing-edge` closes,
after which it too is refused). The defect stands; the summary, step 1 of
`## What's broken` and a note under `## Empirical evidence` were updated in
place. Re-ran `reproduce.py`: still exits 0 — it checks on-disk state, which
is unchanged.
