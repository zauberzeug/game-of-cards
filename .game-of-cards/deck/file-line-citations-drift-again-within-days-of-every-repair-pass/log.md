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
