## 2026-05-27 — CONFIRMED then fixed

Ran the card's falsification recipe verbatim against the live tree: created
`goc/templates/skills/zzz-temp-skill`, synced, removed the source, re-synced.
All four mirrors (`claude-plugin/skills`, `codex-plugin/skills`,
`.claude/skills`, `.codex/skills`) retained an empty `zzz-temp-skill/` dir and
`--check` printed `OK` (exit 0). **DEFECT confirmed**, exactly as hypothesised.

Fix in `scripts/sync_plugin_assets.py`:

- `_sync_dir` + `_sync_codex_skill_tree`: after the file-orphan prune and copy
  passes, walk `dst.rglob("*")` depth-first (reverse sort) and `rmdir` any dir
  that is empty and has no src counterpart. `rmdir` self-guards against
  over-pruning (raises `OSError` on non-empty), so a dir that still holds
  synced content is preserved (DoD item 2).
- `_check_changes` + `_check_codex_skill_tree`: stop blanket-`continue`-ing on
  `is_dir()`; flag an empty orphan dir (no src counterpart / excluded) so
  `--check` FAILs while one remains, closing the rglob blind spot (DoD item 1).

reproduce.py drives the real sync in the live tree (cleaning up after itself),
asserts orphan dirs are pruned, plants empty orphans to prove `--check` now
FAILs and names them, and verifies partial-file-removal does not over-prune.
Exits 0 on the fixed tree. `goc validate` clean; `test_plugin_mirror_parity.py`
12/12 green; `sync_plugin_assets.py --check` green on the live tree.

## 2026-05-27T05:42:00Z — Closure

- **What changed**: `scripts/sync_plugin_assets.py` — `_sync_dir` +
  `_sync_codex_skill_tree` now rmdir empty orphan dirs after the file-prune
  pass; `_check_changes` + `_check_codex_skill_tree` now flag empty orphan
  dirs so `--check` FAILs while one remains.
- **Verification**: reproduce.py exits 0 (was DEFECT pre-fix — all 4 mirrors
  retained empty dirs and `--check` exited 0).
- **Audit**: PASS — no principle touched, mechanical fix (matches the
  intent already shipped by the OpenClaw porter's `shutil.rmtree`).
- **Project impact**: n/a
- **Tests**: test_plugin_mirror_parity.py 12 passed; `goc validate` clean;
  `sync_plugin_assets.py --check` green on the live tree.

## Closure verification (2026-05-27T05:42:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-27 — Closure' section

## Closure verification (2026-05-27T05:42:43Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
