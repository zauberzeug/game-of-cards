
## 2026-07-05 — workflow authored, awaiting first live runs

Implemented `.github/workflows/marketplace-pin-check.yml`. Decision logic
dry-run against live GitHub data (v0.0.26 → `d19aa09a`, pin `4e4c5a1`,
compare → `behind`; self-compare → `identical`; release age 108h > 48h
grace). Card stays **active** until the scheduled run has demonstrated the
issue-create/update/close lifecycle in CI.
