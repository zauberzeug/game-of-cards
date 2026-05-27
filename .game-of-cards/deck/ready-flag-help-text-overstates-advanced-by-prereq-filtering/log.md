## 2026-05-27T06:18:00Z — Closure

- **What changed**: `goc/engine.py:2320-2322` — `--ready` argparse help no longer claims "no non-terminal advanced_by prereqs"; now reads "no active waiting_on impediment", matching `card_is_ready`.
- **Verification**: reproduce.py exits 0 (`mentions 'advanced_by prereq(s)': False`, PASS).
- **Audit**: PASS — invokes the deck's read-pattern guarantee (a cold reader of `--help` must see the real contract); primary source: `make-advances-gate-closure-not-the-pull-queue` (done), which reversed the predicate semantics but missed this string.
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean.
- **Bundled with**: none

## Closure verification (2026-05-27T06:18:08Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
