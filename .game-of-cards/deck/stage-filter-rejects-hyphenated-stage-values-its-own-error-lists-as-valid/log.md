## 2026-07-26T21:42:04Z — Closure

- **What changed**: `goc/engine.py:2734-2751` — `parse_stage_filter` tests exact
  membership in `STAGE_ORDER` before the `"-" in stage_flag` range branch, so a
  hyphenated enum value resolves to itself instead of being misread as a range;
  the redundant trailing membership guard collapsed into one unconditional
  usage error. Mirrors regenerated into `claude-plugin/goc/`, `codex-plugin/goc/`,
  `openclaw-plugin/goc/` by `scripts/sync_plugin_assets.py`.
- **Verification**: card `reproduce.py` exit 1 → exit 0 (`--stage 'pre-alpha'`
  went from `exit 2` to `['pre-alpha']`); `--stage alpha-stable` still returns
  the 3-stage span and `--stage nope-alpha` still exits 2.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 793 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`), +2 new cases in `tests/test_stage_filter.py`;
  `uv run goc validate` exit 0.
- **Follow-up filed**: verifying the range half of the DoD surfaced that a range
  whose LEFT endpoint is hyphenated (`pre-alpha-stable`) is still unspellable —
  the first-hyphen split is chosen before the enum is consulted. Out of this
  card's scope (its DoD tested a range over hyphen-free endpoints) and not
  mechanically determined, since the split-resolution rule needs an ambiguity
  policy. Filed as
  `stage-range-with-hyphenated-left-endpoint-is-unreachable` and cross-linked
  from the Fix section.

## Closure verification (2026-07-26T21:42:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present

## 2026-07-26T21:47Z — Follow-up resolved in the same session

The closure entry above estimated that the residual endpoint gap would need a
separate run to settle an ambiguity policy. Writing the follow-up card's Fix
section settled it from existing deck precedent (report an ambiguous reading,
never guess), so the fix turned out to be mechanically determined and was landed
here as fix-through:
`stage-range-with-hyphenated-left-endpoint-is-unreachable` is closed, with its
own commit. `--stage` now addresses hyphenated stage values both as whole values
(this card) and as range endpoints (that one). No change to this card's verdict
or its own diff.
