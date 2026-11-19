## 2026-11-19T04:54:10Z — Filed as a fix-through

Surfaced while fixing through
`goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck`.
Unlike that card, this defect has nothing to do with the missing-deck notice.
It is in the same function the session had loaded, and the fix is one guard
plus its cases in the existing `--llm` test module. That meets the
fix-through bar: gate-free, one site, and close to the loaded context.

- **Dedup**: the deck grepped for `if not live`, `auditing 0`,
  `empty selection`, `zero live` and `no live card`. Every open card on
  `quality-pass --llm` was checked: the DoD-rewrite, null-fix and
  rewrite-count cards, and the active refine-deck reference card, which is
  about documentation. None covers an empty selection.
  `quality-pass-limit-accepts-negative-values-and-audits-wrong-card-subset`
  (done) kept `--limit 0` as a valid value that audits nothing. It did not
  look at whether `claude` is still started.
- **Verdict**: `reproduce.py` exits 1 on `12f1c755`. All four empty
  selections start the fake `claude` once.
