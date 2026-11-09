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

## 2026-11-09T02:16:03Z: renamed from citation-repair-pass-moves-correct-cites-written-against-code-committed-after-the-card

## 2026-11-09T02:22:09Z — Second instance, opposite direction; retitled and re-scoped

Batch E of the same pass's staleness re-check reported that the
`engine.py` cites on
`auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft`
sat six lines above the code their prose names. They were numbered against
`6d36c3dc^`. That commit landed 37 s before the card's filing commit
`dc484d63`, so this is the earlier-tree mirror of the OpenClaw case. Every
anchored pass since 2026-08-10 tracked the wrong lines; `80268935`
re-anchored them by the prose.

- **Retitled** from `…-written-against-code-committed-after-the-card` to
  `…-when-a-parallel-commit-lands-beside-the-card` (`goc move`), since the
  shape runs both ways.
- **Fix re-scoped.** The first draft declined on "next commit within an hour
  and HEAD still holds its line". That condition misses the earlier-tree case,
  and a window alone is too blunt. At current anchors, ±10 min flags 23 cites;
  only 2 were misread, 9 checked correct, and the rest were declined anyway. So
  the window now triggers a prose read, and the decline applies only when the
  prose does not decide.
- `reproduce.py` now replays both instances (5 of 5 correct cites moved).
- Contribution raised to `medium`, in line with the token-collision and
  trivial-anchor recipe defects: the misread is laundered into a confident
  anchor and survives every later pass.
