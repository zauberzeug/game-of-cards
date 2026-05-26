## 2026-05-26T13:27:47Z — Closure

- **What changed**: `goc/templates/skills/advance-card/SKILL.md` —
  broadened `description` to AUTO-INVOKE on relationship-modeling
  intents ("this is part of X", "make this depend on Y", "should this
  be an edge or a tag?", "unlink these", etc.); added a new
  "Modeling a relationship: edge vs tag" body section with a decision
  procedure, a short-form recap of the three coordinating-card shapes
  (linking out to `Skill(card-schema)` for the full taxonomy), a
  `goc unadvance` retraction sub-section, and a grouping-via-tag note
  pointing at `Skill(card-schema)` "Adding new tags".
- **Verification**: `python scripts/sync_plugin_assets.py --check`
  reports `OK — plugin payloads + dogfood self-host copies match
  goc/ and goc/templates/ byte-for-byte`; `uv run goc validate` walks
  every card with no errors.
- **Audit**: PASS — no rubric configured; documentation-only edit, no
  engine or schema change, no principle binding beyond GoC's own
  "single-source the canonical taxonomy in `card-schema`" convention
  (which is followed: the new section links rather than duplicates).
- **Project impact**: relationship-modeling questions ("should this be
  an edge or a tag?", "make this depend on Y") now have an
  AUTO-INVOKE front door at `Skill(advance-card)`; no new skill
  added, no engine change, no sync/port surface expansion.
- **Tests**: no pytest suite in repo; `goc validate` clean.
- **Bundled with**: none.

## Closure verification (2026-05-26T13:28:13Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
