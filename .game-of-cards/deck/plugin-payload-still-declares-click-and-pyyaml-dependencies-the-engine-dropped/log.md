## 2026-10-17T04:50:00Z — Closure

- **What changed**: `claude-plugin/pyproject.toml` and `claude-plugin/uv.lock`
  deleted. `scripts/sync_plugin_assets.py:60-63` — the `_build_sync_pairs`
  docstring names `claude-plugin/.claude-plugin/plugin.json` where it named
  the manifest. `tests/test_plugin_payload_dependency_manifests.py` (new, six
  tests) derives the payload set from `<dir>/goc/__init__.py`, the bundled
  engine's third-party imports from an `ast` walk, and each tracked
  manifest's runtime declarations, and fails on any declared package the
  engine does not import. A manifest format it cannot read fails outright.
- **Verification**: reproduce.py exit 1 → 0. On the pre-fix tree the new
  live check reported four lines (click and pyyaml in each file); after the
  fix, none. `PreFixManifestFiresTest` gets the same four from the verbatim
  pre-fix `pyproject.toml` and the hash-elided `uv.lock`, checked against the
  real bundled engine. Under Python 3.10 (no `tomllib`) the live check runs
  and passes and the four TOML fixture tests skip.
  `sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check` and
  `goc validate` green.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1331 passed / 0 failed / 0 xfailed (`tests/test_plugin_payload_dependency_manifests.py` 6/6)
- **Bundled with**: none
- **Meta card**: the row is added to
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`'s
  instance table, and its running count is reconciled with `advanced_by` in
  place (37 edges, 27 rows, gap ten).
- **Forward pointer**: a post-close amendment on
  `bundle-goc-engine-inside-plugin-payload`, the card that created both
  files.

## Closure verification (2026-10-17T04:50:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-17 — Closure' present
