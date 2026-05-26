## 2026-05-26T13:20:43Z — Closure

- **What changed**: `goc/templates/skills/{advance-card,card-schema,deck,standup,pull-card,decide-card,retrospective}/SKILL.md` — soft-deprecate `status: blocked` in skill bodies; advance-card drops the `* → blocked` transition row and points to the `waiting_on` overlay / derived dependency-readiness; card-schema marks `blocked` deprecated, retains the three-axis model as the canonical "stuck" reference, and reconciles `STALE_BLOCKED` / `ORPHAN_BLOCKED` as migration aids; deck lifecycle diagram drops the `blocked` branch; standup pivots its second section from `--status blocked` to `waiting_on`-overlay enumeration; pull-card readiness wording corrected to match engine (`card_is_ready`: no `advances`-edge exclusion).
- **Verification**: `python scripts/sync_plugin_assets.py --check` reports `OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte`; `uv run goc validate` lists every card as `OK` with no `STALE_BLOCKED` / `ORPHAN_BLOCKED` / `WAITING_OVERDUE` advisories.
- **Audit**: PASS — no rubric configured; mechanical documentation update aligned with the three-axis model decided in the parent epic.
- **Project impact**: n/a (docs / skill bodies only; the still-accepted enum value keeps existing cards loading).
- **Tests**: n/a (no pytest suite; `goc validate` is the gate, green).
- **Bundled with**: none.

## Closure verification (2026-05-26T13:20:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
