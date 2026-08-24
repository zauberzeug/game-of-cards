## 2026-08-17T05:10:00Z — Pull session priced the options and parked on the pick

Claimed off the ready queue, confirmed the defect still reproduces, then
measured the three fix options against the live deck instead of estimating
them. `reproduce.py` exits 1 at HEAD: the 2026-08-10 pass is now 7 days old
with 227 of its 329 citations (69%) already wrong, against a 25% budget.

The census changed one of the card's own claims and is written back into the
README dashboard in place. The corpus is 845 cite occurrences over 190
open/active cards, deduping to 729 distinct `(path, line)` pairs across 154
cards, all resolvable. It is far more Python-heavy than the filing assumed:

- 615 cites (84.4%) point at `.py`, 450 of them into `goc/engine.py` alone
  and 110 into `goc/install.py`.
- Option B's stated cost — "a resolver for the non-Python surfaces that carry
  a third of the cites" — is wrong by better than 2×. Non-Python is 15.6%,
  and 49 of those 114 are `.md`, where 48 sit under a heading and the
  `§ Heading` form already used in card prose works today. Only 65 cites
  (8.9%) sit on surfaces with no resolver at all.
- Option B's real cost is granularity, not coverage: 543 of 615 Python cites
  (88.3%) resolve to a `def`/`class`, but the 615 cover only 417 distinct
  lines collapsing into 156 symbols — `engine.py::_build_parser` absorbs 22
  separately cited lines across 266 lines of body.
- Option A's migration is 85% mechanical right now: 620 of 729 cites sit on a
  line that is unique in its file and longer than 12 characters. The 109-cite
  residue is 39 repeated lines, 39 trivial, 31 blank — smaller than the 236
  the current recipe declines, because a written anchor needs no history
  recovery. Measured immediately after a repair pass, so it is an upper bound
  that decays with the deck.

Gate raised `none` → `decision`, status returned `active` → `open`, and
`## Fix options` rewritten as a contract-shaped `## Decision required` (DoD
item 2 repointed at it). Two reasons the puller did not pick:

1. The convention is set in a skill shipped to every PyPI/npm/ClawHub
   consumer, so the choice changes the methodology GoC prescribes to repos
   that have never seen this deck, and commits someone to migrating 729 live
   cites. Who pays — author, tooling, or reader — is a judgement, and
   `.game-of-cards/hooks/pull-card.md` defines no project-local rubric that
   answers it, so the Andon cord routes it to the human.
2. No citation form can make a *historical* repair pass survive, so DoD item
   1 can only go green by redefining what `reproduce.py` counts as decay —
   and which redefinition is legitimate follows from the form chosen.
   Weakening a defect test should carry a human's name, not an agent's.

A fourth option the census surfaced is recorded for completeness: symbol plus
anchor with no line number at all, which is B's stability and A's
verifiability at the cost of both migrations and of clickability. Leaning
recorded as A, non-binding, because it is the only option under which a cold
reader can tell whether the cite in front of them is still true.

No code changed. `uv run goc validate` clean.

## 2026-08-24 — hygiene pass: the one-week decay rate reproduced (71%, was 69%)

Ran `reproduce.py` at HEAD before landing that day's repair commit, so the
measurement is of `f290f5f7`'s decay rather than of the pass measuring itself.

```
f290f5f7f     7d    195/273   ( 71%)
69e1e4f22    13d    246/329   ( 75%)
9fa3a2421   110d     60/60    (100%)
```

`f290f5f7` is 71% decayed at seven days — the same age at which `69e1e4f2`
measured 69%. That is the load-bearing addition: the original filing had one
datapoint at one week, so 69% could have been a bad week. Two independent
passes decaying identically seven days apart makes ~70%-at-one-week the
steady-state rate. `goc/engine.py` grew 6979 → 7093 and `goc/install.py`
1838 → 1866 over the interval, with no refactor involved.

The residue also reproduced in shape and size. This pass repaired 286
occurrences across 83 cards and declined: 126 trivial anchors, 89 ambiguous
matches, 44 absent anchors, 1 ambiguous path, and 153 range cites where one
endpoint was unsafe (the recipe rewrites neither endpoint in that case, per
`reference.md` § Citation anchor check). The 2026-08-17 pass declined 236 of
the same three kinds. So the decline residue is a property of the scheme, not
of a given pass's diligence — which is the argument the `## Decision
required` options are priced against.

Two of this pass's declined anchors turned out to matter beyond citation
hygiene: the absent-anchor bucket is what surfaced that two parked
decision-gated cards had been describing an already-fixed defect for two
months. Recorded here because it is evidence for Option A specifically — an
absent anchor is the only signal in the current scheme that says "re-read
this card", and it only fires by accident. Filed as
`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`.

README dashboard rewritten in place with the new datapoint. Gate and status
unchanged; no code changed.
