## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/install.py:31` — broadened `GOC_BEGIN_RE` from
  `[\d.]+` to `[\w.+!-]+` so a PEP 440-suffixed BEGIN-GOC marker is
  re-found and replaced in place instead of duplicated.
- **Verification**: reproduce.py exits 0; all 5 PEP 440 forms match, the
  `<!-- BEGIN GOC IMPORT -->` marker still does not; append-twice leaves
  exactly 1 marker.
- **Audit**: PASS — no principle touched, mechanical fix (regex broadening).
- **Project impact**: n/a
- **Tests**: 159 passed / 0 failed (incl. test_version_surfaces.py);
  `sync_plugin_assets.py --check` and `goc validate` clean.

## Closure verification (2026-05-26T22:58:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
