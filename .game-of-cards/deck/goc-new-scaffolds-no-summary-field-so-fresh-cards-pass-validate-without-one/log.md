## 2026-07-23T04:55:00Z — Closure

- **What changed**: `goc/engine.py` — `validate_card` summary rule now
  fires on an absent key for non-draft cards (message: `<title>:
  summary: missing — required on published cards`); `goc new` gained a
  `--summary` flag (blank values rejected, key emitted right after
  `title`). `goc/templates/skills/create-card/SKILL.md` Step 4 command
  block shows `--summary`, with the Step 5 summary bullet noting that
  validate requires the field once the card leaves draft; the skill was
  trimmed back under its 10,000-byte hot-path cap (9,996 bytes) after
  the additions. Mirrors re-synced (`scripts/sync_plugin_assets.py`,
  `scripts/port_skills_to_openclaw.py`).
- **Decision (DoD MECHANICAL item)**: the `--summary` convenience flag
  DID land — skill-driven filings can now set the summary atomically at
  scaffold time; the validate rule remains the actual guard. Draft
  scaffolds without the flag stay exempt until published/claimed.
- **Verification**: `reproduce.py` exits 0 (validate exit flipped 0 → 1
  on the published summary-less card); `uv run goc validate` exit 0 on
  the real deck.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 758 passed / 0 failed (includes new
  `tests/test_validate_summary_missing.py`: 4 tests)

## Closure verification (2026-07-23T13:00:37Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-23 — Closure' present
