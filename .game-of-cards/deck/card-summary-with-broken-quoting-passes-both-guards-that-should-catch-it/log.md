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

## 2026-11-09T01:00:07Z — Related finding (audit-deck): the strict-YAML guard also misses a TAB at either end of a value

Parked here, not filed separately: audit-deck files one new card per run. This is the same guard missing another shape that a strict reader refuses.

- **Defect:** `scripts/check_card_frontmatter_yaml.py:129-130` runs `value = value.strip()` before the TAB test at `:147` (`elif "\t" in value:`). A TAB right after `key:`, a TAB after the separating space, or a trailing TAB is stripped before the guard looks. The docstring at `:51` claims "YAML admits no TAB anywhere in a plain scalar".
- **Evidence (audit-deck hunter agent, re-checked on the main thread):** `flag_frontmatter` returns `[]` for `'summary:\tfoo bar'`, `'summary: \tfoo bar'`, `'summary: foo bar\t'` and `'status:\topen'`. It flags the control `'summary: foo\tbar'`. PyYAML 6.0.1 refuses all five with `ScannerError: while scanning for the next token`. In a temp deck, `goc validate` (yaml_lite) passes such a card, and the guard's `--check` reports it strict-YAML clean.
- **Reachability:** hand edits only. `emit_frontmatter` quotes any value containing a TAB, so goc verbs do not write this shape.
- **Not yet done:** no `reproduce.py`. Recipe: plant the four forms plus the control in a temp deck and run the guard. Today it prints silent ×4, exit 1. After a fix, all four are flagged and the precision controls stay silent, exit 0.
