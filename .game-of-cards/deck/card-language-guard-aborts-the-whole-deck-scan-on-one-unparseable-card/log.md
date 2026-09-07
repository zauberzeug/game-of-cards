# Log — card-language-guard-aborts-the-whole-deck-scan-on-one-unparseable-card

## 2026-07-31T06:20:00Z — Closure

- **What changed**: `scripts/check_card_language.py:222-238` — `scan_card` nets
  `FrontmatterError`, warns `WARNING: <card>: <exc>` on stderr, and falls back
  to `{}` so the existing slug fallback actually fires; module docstring gained
  the division-of-labour note (`goc validate` owns the malformation, this guard
  owns language).
- **Verification**: `reproduce.py` 3 failing cases → 0, exit 1 → 0. Each case
  now yields 6 findings (control card's 4 + the malformed card's 2, recovered
  from its slug) where it previously yielded a `FrontmatterError` traceback and
  zero. New `EnglishOnlyUnparseableCardTest` (2 tests, 3 subtests) confirmed
  sensitive: all three malformation shapes raise `FrontmatterError` against the
  pre-fix script (`git show HEAD:scripts/check_card_language.py`), so the guard
  cannot silently stop guarding.
- **Audit**: PASS — no rubric configured; mechanical fix. The netting mirrors
  `engine.load_all_cards` (`goc/engine.py:973-979`) — "don't let one broken card
  blank the whole queue" — and the `_cmd_migrate_list_style` fix from
  `goc-migrate-list-style-crashes-on-first-malformed-card-mid-iteration`. No
  consumer-facing surface changes: the guard is repo-local by design, so no
  template, no plugin mirror, no engine edit.
- **Sibling sweep** (DoD PROCESS item): `grep -n "parse_frontmatter" scripts/*.py`
  returns only `check_card_language.py`. The one other repo-local deck-walker,
  `scripts/backfill_terminal_closed_at.py:69`, goes through
  `engine.load_all_cards()`, which is already netted. No further unnetted
  repo-local call site exists; nothing new to file.
- **Project impact**: n/a
- **Tests**: 875 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`). `uv run goc validate` exits 0;
  `uv run python scripts/check_card_language.py --check` reports "English-only:
  clean (692 cards scanned)"; `python scripts/sync_plugin_assets.py --check` OK.

## Closure verification (2026-07-31T06:02:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-31 — Closure' present
