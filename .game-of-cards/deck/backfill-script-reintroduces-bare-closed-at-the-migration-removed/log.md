## 2026-07-26T22:09:59Z — Closure

- **What changed**: `scripts/backfill_terminal_closed_at.py:96` — the
  `closed_at` timestamp now routes through `_yaml_inline` before reaching
  `mutate_frontmatter_field`, matching the three engine closure writers; the
  written value is unchanged, only its quoting.
  `tests/test_closed_at_canonical_form.py` gains `ClosedAtWriterContractTest`,
  which turns the parent card's one-time manual sweep into a static property
  over every `closed_at` writer under `goc/` and `scripts/`, plus an
  anti-vacuity test pinning the scan to the two files that write the field.
- **Verification**: `reproduce.py` exit 1 → 0 (Probe 1: 4/4 writers routed,
  was 3/4; Probe 2: the script's line is now byte-identical to
  `emit_frontmatter`'s). The new contract test was confirmed to fail on the
  pre-fix source (`scripts/backfill_terminal_closed_at.py:85 passes \`ts\``)
  and pass on the fixed one. Deck-wide emitter round-trip: 0 cards whose
  `closed_at` line the emitter would rewrite. `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix (writer/emitter contract
  symmetry — the same contract the parent card established).
- **Project impact**: n/a — repo-local maintenance script, absent from the
  wheel (`packages = ["goc"]`); no consumer-visible behavior change.
- **Tests**: 797 passed / 0 failed / 0 xfailed (2 new).
- **Scope note**: `goc migrate-list-style --dry-run` reports 10 cards, all
  pre-existing **list-style** drift (`advances`/`advanced_by`/`supersedes`/
  `superseded_by` block-style) on cards this closure never touched. It is not
  `closed_at` drift and is not caused by this fix — recorded here so the
  number is not mistaken for a regression. Unfiled; a future hygiene pass owns it.
- **Post-closure amendment to the parent**: this closure also amends the closed
  card `closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter`
  with a `## Post-closure correction (2026-07-26)` section and a log entry —
  its ticked "any other call site" DoD box was false at closure. Per
  "closure is not frozenness", the stale claim is corrected in place and
  forward-linked rather than left standing.

## Closure verification (2026-07-26T22:10:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
