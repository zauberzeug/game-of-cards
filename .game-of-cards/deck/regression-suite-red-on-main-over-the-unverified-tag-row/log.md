## 2026-11-23T02:02:30Z — Staleness re-check

Not surfaced by the as-filed anchor scan: the code its cites name only moved,
so every as-filed anchor text is still in HEAD. The same day's citation pass
re-anchored `tests/test_canonical_tag_rows.py:189` → `:214`; the twice-cited
`:106-113` has drifted too (`_score_unverified` now starts at `:132`) and is
declined as an ambiguous occurrence, left for a reader. Found by that pass's
tag-row survey instead — the card is stale by content.

Reproducer: `reproduce.py` → exit 0, "PASS: every live card satisfies its
state rows." (192 live cards scored, offenders `[]`).
`uv run python -m unittest tests.test_canonical_tag_rows` → 10 tests OK.

The offender named in the summary,
`openclaw-pattern-check-never-fires-on-plain-file-edits`, left `unverified` in
`f290f5f7` (the 2026-08-17 hygiene pass), which ran that card's falsification
recipe against openclaw 2026.5.7 and confirmed the defect; its tags are now
`[bug, infra, api-contract]`. So the red suite cleared eleven days after this
card was filed, by promotion on evidence rather than by either option in
`## Decision required`, and no decision was recorded here.

Verdict: no longer reproduces — left at its gate for a human to retire.
Gate unchanged.
