## 2026-09-14 — closed

One predicate, moved one step earlier, plus the guard that keeps it there.

### The recipe

`goc/templates/skills/refine-deck/reference.md` § Citation anchor check —
the **Deciding** paragraph no longer opens on the comparison. It refuses
the anchor line first: a blank, a bare brace, or anything under roughly 12
characters matches everywhere, so re-finding it at the cited offset is no
more evidence that the cite is current than it is evidence of where the
cite should move. That verdict is a DECLINE, reported, never `current`.
Only a substantial anchor is compared, and only then relocated.

Moving the predicate made step 4's copy of it dead text — nothing reaching
the relocate step can carry a trivial anchor any more — so what is left
there is the uniqueness test and a pointer back. A new paragraph, **One
predicate, both directions**, records why the asymmetry was a defect
rather than a rough edge, and the residue table's first row was widened
from "trivial anchor line" (an address that cannot be relocated) to
"trivial anchor, verdict undecidable" (a cite that cannot be decided in
either direction). The table stays at four decline reasons.

Two further edits keep the accounting honest. The reference now says to
expect MORE residue in the first pass after the fix and to read that as
accounting caught up rather than as a regression — 46 cites move out of a
silent `current` and into a table a human reads. And `SKILL.md`'s summary
line went from "Cites step 4 declines — anchor gone, ambiguous, or
trivial" to all four reasons, which it had been under-counting since the
range card added the fourth.

`tests/test_skill_body_size.py` raised the `refine-deck` cap 12_500 ->
12_800 with the rationale, following that file's convention. Sixth raise;
the reasoning is the fourth and fifth raises' sharpened, because the
verdict this catches emits no output at all, so a pass that does not
already carry the rule has nothing to go look it up from.

### The guard

`tests/test_refine_deck_citation_anchor.py` — the file that already holds
the three earlier per-step gaps in this recipe — gained:

- `documented_decide_guard(prose)`, which classifies the shipped prose on
  ORDER, not on vocabulary: the predicate has to be named before the
  verdict and has to name the decline it produces. The control feeds it
  the exact paragraph this card replaced and asserts UNGUARDED — the
  paragraph that NAMES the predicate, one step too late, which is why it
  read as complete for a year.
- `TrivialAnchorDecideTest`, a two-commit fixture built from the module's
  existing `V1` and `INSERT_1` because between them they already held the
  coincidence: a cite on the blank line directly above
  `def target(payload):`, and a five-line insert ending in a blank, so
  HEAD's line 5 is blank too. The unguarded recipe verdicts it `current`
  while the function it names has moved to line 11; the shipped recipe
  declines. A third case exercises the predicate on braces and short
  lines directly.
- `trivial_anchor()` extracted as one function used by both `decide()` and
  `relocate()`, so the model cannot drift into two predicates the way the
  prose did.

Confirmed red-then-green: reverting `SKILL.md` step 3 to the one-line
pre-fix sentence turns three of these tests red; restoring it turns them
green.

### reproduce.py

Rewritten from a census into a census plus a classifier. It now reads the
two shipped surfaces (`SKILL.md` step 3, `reference.md`'s **Deciding.**
paragraph), reports each as guarded or unguarded, and derives the
`current` count from that verdict rather than assuming the pre-fix rule.
The census loop is untouched and was checked against the pre-fix script on
the same tree — both report 639 anchor matches, 44 on a line the predicate
refuses, over 27 cards. What changed is the disposition: 0 of them are
certified, because the shipped recipe declines and reports them. Exit 0.

The 46-of-413 transcript in the card body is the measurement at filing
time, kept as the dated record it is; the drop to 44 is this card's two
hand repairs landing, and the rise to 639 is the same round's new cards.

### Left open

The two siblings filed the same round are untouched by this fix and stay
open: the relocate step still declines a moved function whose definition
line gained a parameter, and the anchor walk still gives two cites in one
card the same anchor when their numbers collide. The convention-level
question — whether a bare line number should address code at all — stays
parked on `file-line-citations-drift-again-within-days-of-every-repair-pass`.
This card holds only the narrower invariant, which any convention has to
keep: a verdict that rests on a brace is worthless under it too.

## Closure verification (2026-09-14T04:43:36Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-09-14 — Closure' section

## 2026-09-14T04:45:00Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md` §
  Citation anchor check (**Deciding**) + `SKILL.md` step 3 — the recipe's
  non-triviality predicate now runs BEFORE the anchor/HEAD comparison, so a
  cite whose anchor line is a blank, a bare brace, or under ~12 characters
  is DECLINED and reported rather than certified `current`; the residue
  table's trivial row widened to "trivial anchor, verdict undecidable".
- **Verification**: `reproduce.py` — 639 anchor matches over the open/active
  deck, 44 on a line the predicate refuses across 27 cards, 0 of them
  certified `current`, exit 0 (was exit 1 with all 44 certified). Reverting
  `SKILL.md` step 3 turns 3 of the new tests red; restoring it turns them
  green. Mirror guards clean: `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check`. `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1117 passed / 0 failed / 0 xfailed (24 in
  `tests/test_refine_deck_citation_anchor.py`, up from 16).
- **Bundled with**: n/a

## Closure verification (2026-09-14T04:43:49Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-09-14 — Closure' present
