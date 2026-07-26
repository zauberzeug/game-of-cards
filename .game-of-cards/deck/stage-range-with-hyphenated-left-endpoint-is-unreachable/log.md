## 2026-07-26T21:46:17Z — Closure

- **What changed**: `goc/engine.py:2737-2764` — the `--stage` range branch
  collects every hyphen position whose two halves are both in `STAGE_ORDER`
  instead of splitting at the first hyphen; one candidate resolves to the span,
  zero keeps the existing usage error, and two or more exit 2 naming both
  readings. Mirrors regenerated into `claude-plugin/goc/`, `codex-plugin/goc/`,
  `openclaw-plugin/goc/` by `scripts/sync_plugin_assets.py`.
- **Verification**: card `reproduce.py` exit 1 → exit 0. `--stage
  pre-alpha-stable` went from `exit 2` to the 4-stage span; the ambiguous
  `--stage alpha-beta-stable` went from silently returning `['alpha', 'beta',
  'alpha-beta', 'beta-stable']` to exit 2 naming `'alpha'..'beta-stable'` and
  `'alpha-beta'..'stable'`. On the shipped hyphen-free enum nothing changed:
  `goc --stage alpha` still filters and `goc --stage foo-bar` still exits 2 with
  the same message.
- **Audit**: no rubric configured; the ambiguity policy (report, never guess)
  follows the deck's attested convention for silent-misparse defects, cited in
  the card's Fix section.
- **Project impact**: n/a
- **Tests**: 795 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`), +2 new cases in `tests/test_stage_filter.py`;
  `uv run goc validate` exit 0.
- **Worked as fix-through**: filed and closed in the same session as its sibling
  `stage-filter-rejects-hyphenated-stage-values-its-own-error-lists-as-valid`,
  whose closure entry had estimated this would need a separate run for an
  ambiguity policy. Writing this card's Fix section settled that policy from
  existing deck precedent, so the fix was mechanically determined after all and
  landed here with the function already loaded. Kept as its own card and its own
  commit.

## Closure verification (2026-07-26T21:46:36Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
