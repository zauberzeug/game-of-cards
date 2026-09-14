## 2026-09-14 — closed

One walk, pinned to an occurrence — and the close-out that finds the next
one of these.

### The recipe

`goc/templates/skills/refine-deck/reference.md` § Citation anchor check —
**Getting the anchor** no longer tests presence with a substring search.
The pass extracts each historical version's cite tokens with the same
pattern it uses to find cites in the card and asks for membership, so
`path:N` stops reading as present inside a `path:N-M` the same card
carries. A new paragraph, **Why the presence test has to be
token-exact**, records why the shipped wording hid this for a month: it
called the token *exact*, and the word modified the token while the test
around it was still `in`.

The convergence half has no such fix, so it is a decline. **One token at
two occurrences — DECLINE** tells the pass to count occurrences before
walking and to stop there when a token appears more than once: those
occurrences share one history and token-exactness cannot separate them
either, because the token genuinely WAS present at the earlier commit, at
the other occurrence. The residue table went from four decline reasons to
five, with *ambiguous occurrence (>1 in the card)* first, since it fires
before the anchor is even computed.

The card's belt-and-braces rule went in as stated: a cite that already
resolves at HEAD is not a repair candidate. It is not the fix — it
silences the symptom for cites that happen to be right and does nothing
for one genuinely defunct and anchored on a neighbour's history — but it
would have stopped all three of the filing measurement's false repairs on
its own, and it is nearly free.

**Close the step by re-running it** is the fourth edit and the one that
generalizes: after applying, run the decision phase again over the cards
just written and assert zero further repairs. Every per-cite rule passes
on a second-round proposal — real anchor, unique match, confident rewrite
— so the re-run is the only thing that sees a pass repairing its own
output, and it is how this class was found at all. A non-empty second
round is a recipe defect to file, not more rewrites to apply.

`SKILL.md` step 2 carries the membership test and the repeated-token
decline in condensed form, its decline list widened from four reasons to
five, and its citation step now ends on the re-run. The edit landed once
in `goc/templates/skills/refine-deck/`; the pre-commit sync and the
OpenClaw porter propagated it to the five mirrors.

`tests/test_skill_body_size.py` raised the `refine-deck` cap 12_800 ->
13_600 with the rationale, following that file's convention. Seventh
raise; its reasoning is the fourth through sixth raises' sharpened
one more turn — every per-cite rule PASSES on the repair this produces,
so a pass carrying only a pointer has no symptom that would send it
looking the rule up.

### The guard

`tests/test_refine_deck_citation_anchor.py` — the file that already holds
the four earlier per-step gaps in this recipe — gained:

- `documented_occurrence_rule(prose)`, which demands both halves: set
  membership over the version's extracted tokens, and the decline for a
  token the card holds at two or more occurrences. Its control feeds it
  the exact sentence this card replaced and asserts TOKEN_WALK — the
  sentence that says "exact" and reads as precise already.
- `documented_idempotence_check(prose)`, with the shipped closing
  sentence it replaced as the negative control.
- `CollidingCiteAnchorTest`, a four-commit fixture built to make both
  readings *confident*: a card carries a range over the target block and
  a single-line cite inside the helper above it, the file grows, a pass
  repairs both, and the number the single cite lands on is one the RANGE
  spelled at the filing commit. The substring walk then anchors the
  helper cite on the target's `def` line and relocates it there —
  uniquely, non-trivially, passing every existing guard — while the
  membership walk relocates it onto the helper's own return. Its third
  case commits the convergence shape and asserts the decline.
- `ResidueAccountingTest`, which ties the reference's stated decline
  count and the core skill's decline list to the rows the table actually
  carries. That is the accounting failure the previous card found after
  the fact: the range card added a fourth reason and `SKILL.md` kept
  saying three for a week.

Confirmed red-then-green: reverting `SKILL.md` step 2 turns five of these
tests red and `reproduce.py` back to exit 1; restoring it turns them
green. 1131 tests pass, up from 1117.

### reproduce.py

Rewritten from a census into a census plus a classifier, following the
shape the previous card in this family established. It reads the two
shipped surfaces (`SKILL.md` step 2, `reference.md` § Citation anchor
check), reports each as guarded or unguarded, and derives the count of
mis-anchored rewrites from that verdict rather than from the pre-fix
rule. The census loop is unchanged: 903 in-scope cites over the
open/active deck, 2 where the two readings of the presence test pick
different anchor commits with different anchor text, 63 cards holding one
in-scope token at two or more occurrences. Under the shipped recipe, 0 of
them is rewritten from another cite's anchor. Exit 0.

### The DoD's first item was amended at closure

As filed it asked for `reproduce.py` to exit zero because "the token walk
and the occurrence-aware walk agree on the anchor commit for every
in-scope cite" — and that is not achievable by fixing prose, nor is it
the right target. The two walks are two readings of the presence test
over the deck's own history; their disagreement is the defect's footprint
in committed data and it survives any recipe change. What the fix can
deliver, and what the box now reads, is that no cite the SHIPPED recipe
would rewrite is anchored from a different cite's history. The census
still prints both disagreements so the footprint stays visible.

### Left open

The relocate-side sibling filed the same round is untouched and stays
open: the recipe still declines a moved function whose definition line
gained a parameter. The convention-level question — whether a bare line
number should address code at all — stays parked on
`file-line-citations-drift-again-within-days-of-every-repair-pass`. The
card's third non-goal also stands: retro-auditing past passes for cites
already moved this way is worth doing and now has a trustworthy walk to
compare against, but nobody has filed it.

The 63-card at-risk population is the part this fix does not shrink. The
decline keeps those cites from being moved from the wrong occurrence's
history, at the cost of not repairing them at all; the passes go on
manufacturing the shape, because neighbouring cites drift together and
get corrected together. If that residue row grows past a reader's
patience, the answer is the parked addressing-convention decision, not a
cleverer walk.

## 2026-09-14T05:02:00Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md`
  § Citation anchor check (**Getting the anchor**) + `SKILL.md` step 2 —
  the anchor walk's presence test is now set membership in the version's
  extracted cite tokens instead of a substring search, and a token a card
  holds at two or more in-scope occurrences is DECLINED (fifth residue
  row) rather than rewritten from one occurrence's history; the citation
  step now closes by re-running the decision phase and asserting zero
  further repairs.
- **Verification**: `reproduce.py` — 903 in-scope cites over the
  open/active deck, 2 where the two readings of the presence test pick
  different anchors, 63 cards holding a repeated in-scope token, 0 cites
  the shipped recipe would rewrite from another cite's anchor, exit 0
  (was exit 1 with both relocated onto the line above the function their
  card names). Reverting `SKILL.md` step 2 turns 5 of the new tests red
  and `reproduce.py` back to exit 1; restoring it turns them green.
  Mirror guards clean: `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check`. `uv run goc validate`
  exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1131 passed / 0 failed / 0 xfailed (38 in
  `tests/test_refine_deck_citation_anchor.py`, up from 24).
- **Bundled with**: n/a

## Closure verification (2026-09-14T05:00:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-09-14 — Closure' present
