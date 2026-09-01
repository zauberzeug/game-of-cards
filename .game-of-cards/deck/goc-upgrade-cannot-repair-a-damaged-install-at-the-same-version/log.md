## 2026-09-01T05:30:00Z — Closure

- **What changed**: `goc/install.py:1981` — `upgrade()`'s "nothing to do"
  verdict is now `plan_has_effect`, read off `_plan_upgrade_writes` (`:1066`),
  which labels every planned write by asking its own executor rather than
  re-listing the executor's steps. `_upgrade_write_action` (`:1019`) dispatches
  on a new `PlannedWrite.kind` and either compares the bytes the copy would
  write or calls the executor with `probe=True`; `_append_marker_block`,
  `_sync_claude_import`, `_strip_claude_import`, `_append_precommit_hook`,
  `_merge_claude_settings` and `_write_skills_source` all gained that mode and
  share one `_commit_text` primitive (`:220`), so the answer and the write
  cannot diverge. `pending_precommit_refresh` and `_precommit_refresh_pending`
  are deleted — the plan's pre-commit entry covers the drifted stanza the
  predicate handled *and* the absent config it did not. `and not dry_run` is
  gone from the guard, so preview and real run print one verdict.
- **Verification**: `reproduce.py` exits 0 (was 1) — 4/4 repairs performed by
  bare `goc upgrade` at the same version, 0/4 skipped. Pristine repo still
  prints exactly `already at goc X — nothing to do.` with a byte-and-mtime
  snapshot of the whole tree unchanged. `uv run goc validate` exit 0 (743
  cards). `sync_plugin_assets.py --check`, `port_skills_to_openclaw.py
  --check`, `check_card_language.py` and `check_card_frontmatter_yaml.py` all
  clean.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is the
  comment stub). The closure does bind a documented principle rather than being
  purely mechanical: AGENTS.md's derive-don't-re-enumerate rule, stated there
  for the hook list ("derived from `templates/hooks/*.py` at install time … The
  event mapping is not derived — it stays explicit") and applied twice before
  in `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
  and `repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses`. The
  card filed itself at `human_gate: none` on exactly that precedent, and the
  fix follows it: the guard now reads one computation instead of a
  hand-maintained register. AGENTS.md gained a paragraph forbidding a new
  `pending_*` term so the next writer does not restore the pattern.
- **Project impact**: consumers on a plugin-delivered engine — where
  `.goc-version` matches for the whole life of a release — get a working
  `goc upgrade` between releases for the first time. `goc install`'s
  "Run `goc upgrade` to re-sync templates" refusal stops being a dead end.
  The dry-run preview is also newly truthful: it labels already-current writes
  `unchanged` and reports `(N effecting)` in its header.
- **Sensitivity**: measured — forcing `plan_has_effect = False` (the retired
  allowlist's blindness) fails 8 of the 15 tests across the two upgrade
  modules, including the predecessor card's own stale-glob migration, and
  returns `reproduce.py` to exit 1. The synthetic-pending-write test fails on
  any guard that stops consulting the plan, independent of which repairs
  happen to be un-registered today.
- **Tests**: 1059 passed / 0 failed / 0 xfailed (was 1047; +12 new).
- **Bundled with**: n/a. The forward pointer required by the DoD was appended
  to `goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration`
  (done) rather than reopening it — the behavior that card established is
  unchanged, only the mechanism behind it moved.

## Closure verification (2026-09-01T04:52:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-09-01 — Closure' present
