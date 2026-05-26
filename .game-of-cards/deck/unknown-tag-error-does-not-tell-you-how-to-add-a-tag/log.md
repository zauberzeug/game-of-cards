## 2026-05-26T13:33:15Z — Closure

- **What changed**: `goc/engine.py` — added module-level
  `_UNKNOWN_TAG_REMEDY` constant naming the
  `.game-of-cards/canonical-tags.md` mechanism (project-local tag) and
  the goc-PR path (generic tag); wired it into all three rejection
  sites (validate, `--tag` filter, `goc new`). Dropped the
  "(not in SCHEMA.md canonical_tags)" suffix at the two sites that
  still cited the wrong file. Added a "Need a new grouping tag?"
  pointer to `goc/templates/skills/create-card/SKILL.md` next to the
  introduction of `--tag`.
- **Verification**: ran each rejection site against an unknown tag and
  confirmed the new wording shows the remedy; created a fresh tag in a
  scratch `.game-of-cards/canonical-tags.md` and verified
  `goc new --tag <newtag>` succeeds without the file the same tag was
  rejected; `tests/test_tag_filter` passes (the existing
  `"unknown tag 'not-a-real-tag'"` substring assertion still holds).
- **Audit**: PASS — no rubric configured; mechanical fix
  (error-message + skill-doc discoverability, no contract change).
- **Project impact**: n/a (no project dashboard).
- **Tests**: 2 passed (`tests.test_tag_filter`).
- **Bundled with**: n/a.

## Closure verification (2026-05-26T13:33:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
