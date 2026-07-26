## 2026-07-26T05:57:52Z — Closure

- **What changed**: `.github/workflows/pull-card.yml:102`, `.github/workflows/audit-deck.yml:78`, `.github/workflows/refine-deck.yml:82` — added `--effort max` to each `claude_args` block, directly after `--model opus`.
- **Verification**: `claude --help` on the local CLI (2.1.220) documents `--effort <level>` with levels `(low, medium, high, xhigh, max)`; `grep -A5 claude_args` on each workflow shows the flag present once, at the same 12-space indentation as its siblings inside the literal block scalar.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: unattended pull/audit/refine runs now reason at maximum effort on Opus. Token spend per run rises, compounding with the 3h/1d/1d cadence set in `10bd545a` — accepted and recorded in the card body under "Cost consequence" so a future spend investigation finds the cause.
- **Tests**: n/a (workflow config edit; `goc validate` clean, `sync_plugin_assets.py --check` clean)

## Closure verification (2026-07-26T05:57:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
