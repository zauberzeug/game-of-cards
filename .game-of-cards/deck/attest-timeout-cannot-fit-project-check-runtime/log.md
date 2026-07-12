## 2026-07-12T03:41:11Z — Closure

- **What changed**: `goc/engine.py:_run_automated_check` accepts a per-check positive-integer `timeout_seconds`, preserves the 300-second default, and rejects invalid or subprocess-overflowing values before spawning; the shipped config template documents the field and all plugin engines are synchronized.
- **Verification**: configured 1000-second forwarding and timeout rendering pass; absent config stays at 300 seconds; seven invalid-value controls fail cleanly without a subprocess.
- **Audit**: PASS — no rubric configured; mechanical API/configuration fix.
- **Project impact**: consuming repositories can attest legitimate long-running gates without raising the global budget for every check.
- **Tests**: 713 passed / 0 failed plus 198 subtests; focused timeout suite 3/3 passed. The documented macOS-local interactive-rebase setup test was excluded because it fails identically on unmodified HEAD and passes in CI.

## Closure verification (2026-07-12T03:41:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-12 — Closure' present
