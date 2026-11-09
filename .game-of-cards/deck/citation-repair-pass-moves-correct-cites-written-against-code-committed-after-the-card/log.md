## 2026-11-09T02:14:07Z — Filed by the refine-deck hygiene pass

Found while closing the pass's citation step. The pass applied 319 anchored
repairs, and its belt-and-braces check (does the prose name a symbol at the
current number but not the new one?) flagged one: `index.ts:763` on the
OpenClaw hooks card, which was held. Reading why showed that its sibling
`:797` had passed the check for the wrong reason and was already applied. Both
cites were written against `ffc0f4bc`, committed six minutes after the card.
`2195ec34` restored `:797` and logged the hold on that card.

Dedup: nine cards carry the citation recipe's history. Eight closed recipe
defects cover the bounds test, the creating-commit anchor, fences, ranges,
trivial anchors, token collisions, definition lines that gained a parameter,
and the commit-before-re-run order. The
open `file-line-citations-drift-again-within-days-of-every-repair-pass` asks
whether to leave bare line numbers altogether. None covers a number computed
against a tree other than its anchor commit's.

Filed at `human_gate: none` with a concrete rule, because the census
separates the shape cleanly on this deck: 2 true cases, 0 false ones. The
recipe's existing stance (decline rather than guess) settles what to do with
a hit.
