# Log

## 2026-06-09 — Reword landed; parked on release authorization

- **Claimed** by claude[bot] (pull-card) and implemented DoD 1–3:
  reworded the Stop-hook REMINDER from a binary (file / don't) to a
  three-branch form (NO / dedup-then-CONNECT-to-existing-root / file),
  synced all 7 Python copies + the OpenClaw TS port, rebuilt the
  OpenClaw bundle (which also brought the previously-stale `dist/`
  current), and added `ReminderWordingTest`.
- **Verified**: `uv run python -m unittest discover -s tests` → 413
  pass; `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` both clean.
- **Committed** to main as `fix(pattern-check-hook): reword Stop-hook
  REMINDER to three-branch form` (ced3cd0).
- **Parked** at `human_gate: session`. Only DoD item 4 (version bump +
  release) remains — an irreversible publish to PyPI/npm/ClawHub and a
  release-cadence call for the maintainer (see "Decision required" in
  README). Item 5 (single-sourcing) deferred to follow-on card
  `single-source-pattern-check-reminder-across-host-ports`.
