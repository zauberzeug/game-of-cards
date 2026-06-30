## 2026-06-30T02:18:57Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` `_split_flow` — quote-mode now opens only at a node-start position (start, or after `,`/`:`/`[`/`{`), so a bare apostrophe in an unquoted flow element is content, not a quote opener. A quoted value that legitimately begins after `key: ` still delimits.
- **Verification**: `reproduce.py` exits 0 (PASS); `worker: {who: o'connor, where: feature/x}` now parses to `{'who': "o'connor", 'where': 'feature/x'}` (was 1 corrupted key). New `BareQuoteFlowSplitTest` (5 cases) green; 4 pre-existing scanner regression tests unchanged.
- **Audit**: PASS — no project rubric configured (hook empty); mechanical parser-correctness fix, no project principle touched.
- **Project impact**: n/a
- **Tests**: 682 passed / 0 failed (full `unittest discover -s tests`); `goc validate` clean; `sync_plugin_assets.py --check` green.
- **Bundled with**: n/a
- **Note**: 5th concrete instance of the drift catalogued by [yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/) (wired via `advances`); that meta-fix remains the way to stop future divergence.

## Closure verification (2026-06-30T02:19:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-30 — Closure' present
