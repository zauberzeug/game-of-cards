## 2026-05-29T11:15:48Z — Closure

- **What changed**: `goc/engine.py:3255` (`_cmd_done`), `goc/engine.py:3341`
  (`_cmd_done_bundle`), `goc/engine.py:4001` (`do_status` disproved/superseded)
  — route `_utc_now_iso()` through `_yaml_inline()` so the closure-verb
  writer matches the emitter's canonical quoted form. Migration pass
  normalized 128 deck cards (127 had bare-datetime `closed_at`).
- **Verification**: `reproduce.py` exits 0 with `drift: False`; new
  `tests/test_closed_at_canonical_form.py` covers `done`, `done --bundle`,
  `status disproved`, `status superseded` — all four assert byte-identity
  between the closure-verb's `closed_at` line and `emit_frontmatter`'s
  output; verified the test fails without the engine fix and passes with it.
  `uv run goc migrate-list-style --dry-run` now reports zero rewrites.
- **Audit**: PASS — no rubric configured; mechanical fix (writer/emitter
  contract symmetry).
- **Project impact**: n/a — internal contract fix; no user-facing behavior
  change beyond consistent on-disk closure form.
- **Tests**: 230 passed / 0 failed / 0 xfailed (4 new tests in the
  closed_at canonical-form suite).

## Closure verification (2026-05-29T11:16:01Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

## 2026-07-26 — Post-closure amendment (sweep gap)

- **Trigger**: an `audit-deck` pass enumerated every
  `mutate_frontmatter_field(..., "closed_at", ...)` call site in the tree and
  found one that bypasses `_yaml_inline` —
  `scripts/backfill_terminal_closed_at.py:85`.
- **What this means for this card**: the ticked MECHANICAL box asserting that
  "any other call site ... for a colon-bearing value" was routed or documented
  was false at closure. The sweep behind it only walked `goc/engine.py`.
- **What is NOT affected**: the engine fix (three writers) and the 251-card
  migration both held. Re-audited 2026-07-26: the deck carries 378 quoted full
  timestamps, 125 bare date-only values (correct — no colon, so the emitter
  leaves them bare), 173 nulls, and zero bare full timestamps outside a fenced
  code sample in this card's own README.
- **Follow-up**: filed and closed
  `backfill-script-reintroduces-bare-closed-at-the-migration-removed`, which
  routes the script's timestamp through `_yaml_inline` and replaces this card's
  one-time manual sweep with a static property test over every `closed_at`
  writer under `goc/` and `scripts/`.
- **Body**: `## Post-closure correction (2026-07-26)` section added to
  README.md; the stale claim is corrected in place rather than left standing
  with a note below it.
