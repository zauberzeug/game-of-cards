## 2026-09-16 — the hazard materialized; body amended, gate untouched

An audit pass measured this guard against PyYAML over the live deck and found
one false negative: `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries`,
filed 2026-08-31 — eight days after this card was filed — carries a double-quoted
`summary` with unescaped interior quotes. PyYAML raises `ParserError` on the
block while `goc validate`, `scripts/check_card_frontmatter_yaml.py --check` and
CI all report clean. Route 1 of `## Reachability`, exactly as written.

Amended in place: the `## Why it matters` severity paragraph no longer claims a
clean live deck, the route-1 counts are re-measured (114 of 759 summaries carry
an escaped interior quote, up from 105 of 732), and the frontmatter summary says
the hazard has landed. `## Decision required`, the DoD and `human_gate: decision`
are deliberately untouched — the three fix paths still need a human pick.

The instance itself is repaired and guarded by
`deck-ships-a-card-whose-frontmatter-no-standard-yaml-reader-can-parse`, which
pins already-quoted summaries against `emit_frontmatter` from the regression
suite. That net is deliberately narrower than any path below (cards only, the
`summary` field only, a test rather than the pre-commit guard, no change to
`flag_frontmatter`), so it does not pre-empt this decision.
