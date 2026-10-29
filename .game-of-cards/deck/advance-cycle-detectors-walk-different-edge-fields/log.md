
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

## 2026-10-22T05:56:36Z: decision recorded

Lower the gate: verify the hypothesis with a reproduce.py first, then make both cycle walkers read one edge field — Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none. Gate decision → none.

## 2026-10-29 — Verdict: divergence confirmed both ways; both walkers read `advances`

Claimed from the ready queue. `reproduce.py` (new this session) builds
three-card decks whose logical edges a→b→c→a sit in one field only, plus
two controls (the cycle in both fields, an acyclic chain), and compares the
gate's verdict (`detect_advance_cycles` reports anything) with the guard's
(`_would_create_advance_cycle` refuses one of the deck's own edges). Against
the pre-fix engine it exits 1:

```
advances-only     validator sees cycle: False  guard sees cycle: True   -> DISAGREE
                    repair-edges: 0 fixable, 3 structural
advanced_by-only  validator sees cycle: True   guard sees cycle: False  -> DISAGREE
                    repair-edges: 2 fixable, 1 structural
both fields       validator sees cycle: True   guard sees cycle: True   -> agree
acyclic chain     validator sees cycle: False  guard sees cycle: False  -> agree
```

So the hypothesis holds, and in both directions, not just the filed one.
The filed bound is true but answers a different question.
`validate_bidirectional_edges` keeps half-edges off any deck `goc validate`
accepts. The walkers do not only run there: the gate runs inside a failing
`goc validate`, and `goc repair-edges` consults the guard on half-edged
decks alone. The 08-31 and 09-07 passes worried that the fixture is a state
no verb creates. That is true, and it is also the state `repair-edges`
exists to operate on.

PROCESS verdict: one field, as the 2026-10-22 decision directs, and that
field is `advances`. The guard already walks it and is pinned by the
`repair-edges` regression tests, so moving the read-only gate leaves every
write path as it was. It is also the field `compute_values` walks, whose
docstring names this gate as what keeps its input acyclic. A cycle there
silently yields order-dependent priorities, while an `advanced_by` cycle
stalls closure loudly through `advanced-by-closed`.

Considered and not taken: walking the union of both fields, so an edge
counts when either half records it. It would see every recorded cycle, and
it is the edge set `repair-edges` already assumes by completing half-edges
rather than dropping them. It departs from the decision's single field,
though, and changes `repair-edges` behavior: an `advanced_by`-recorded cycle
would get every edge refused instead of all but one repaired, re-pinning
`test_repair_edges_dry_run_matches_apply_on_interacting_half_edges`. That is
a call for a human. The cost of the single field is that a cycle recorded
only in `advanced_by` is now read by neither walker (the gate used to report
it). It stays bounded: its half-edges fail validation, and `repair-edges`
refuses the edge that would close it in `advances`.

## 2026-10-29T05:09:51Z — Closure

- **What changed**: `goc/engine.py:2298` `detect_advance_cycles`, the `goc validate` cycle gate, now walks `advances` instead of `advanced_by`. That is the field `_would_create_advance_cycle` (`goc/engine.py:2334`) and `compute_values` read. Its error names the field it walked and draws the value-flow arrow the guard's refusal uses: `a: advances: cycle detected through c → a`. Both walkers' docstrings name the shared field, and the gate's names the residual. Synced to the three plugin engine mirrors.
- **Shape**: one field, per the 2026-10-22 decision, and `advances` for the reasons in the verdict entry above. The union of both fields was weighed and left for a human, because it changes `repair-edges` classification.
- **Reproducer**: new, under the 0/1/2 contract. It runs four fixtures (cycle only in `advances`, only in `advanced_by`, in both, and an acyclic chain), with the last two as controls that exit 2 if misjudged. It exits 1 against the pre-fix engine, where both one-field fixtures disagree, and 0 after the fix.
- **Verification**: `reproduce.py` exits 0. `tests/test_advance_cycle_walkers_agree.py` has 5 tests; 3 fail against the pre-fix engine (HEAD's `engine.py` in a scratch copy) and the 2 controls pass on both. The non-list test in `tests/test_non_list_advances_guard.py` used to feed the gate a bare-string `advanced_by`, a field it no longer reads, so it now feeds a bare-string `advances`. It fails when the walker's `isinstance` guard is removed.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1428 passed / 0 failed (`uv run python -m unittest discover -s tests`). After that run only a docstring changed, and the mirror-parity and walker tests were re-run green.

## Closure verification (2026-10-29T05:09:55Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-29 — Closure' present

## 2026-10-29T05:15:16Z — Post-close amendment

Extended by [`advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks`](../advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks/). This card's gate/guard split is one instance of a wider one: ten consumers of the advances relation each read one half of an edge and split three to three on a half-edged deck. The union-of-both-halves option this card left for a human is that card's decision (gate `decision`), and this card now advances it.
