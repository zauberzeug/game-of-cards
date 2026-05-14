## 2026-05-14T11:30:52Z — Closure

- **What changed**: `goc/engine.py:2862,2890,2434,2373` — engine-written
  log.md headers (rename, decision-recorded, closure-verification) now
  use `_utc_now_iso()` instead of `date.today().isoformat()`; the
  `log-md-closure-entry` derived check accepts both date-only and
  datetime closure-header forms via a date-prefix regex. The
  `finish-card` skill (Claude + OpenClaw copies) documents the new
  `## YYYY-MM-DDTHH:MM:SSZ — Closure` form.
- **Verification**: `uv run goc validate` clean across the deck; the
  closure-marker regex was smoke-tested on six legacy / datetime /
  mismatch / off-day cases — all pass.
- **Audit**: PASS — symmetric with the predecessor
  `record-card-timestamps-as-utc-datetime`; the
  "be liberal in what you accept, strict in what you emit" posture
  carries from frontmatter into log.md without backfill.
- **Project impact**: n/a (no project-DoD layer-2 dashboard).
- **Tests**: no pytest suite; CI smoke covers build + console-script +
  `goc validate` on Python 3.10–3.13.
- **Bundled with**: incidental `.pre-commit-config.yaml` fix —
  `python` → `uv run python` on the `sync-plugin-assets` entry, to
  match CI's invocation since `python` was not resolvable in the
  shell that ran pre-commit.

## Closure verification (2026-05-14T11:31:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-14 — Closure' present
