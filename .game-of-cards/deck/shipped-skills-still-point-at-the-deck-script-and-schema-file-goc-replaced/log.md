## 2026-10-04T07:10:00Z — Filed

Surfaced while closing
`deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects`,
whose fix edited the same deck skill. Dedup: no open card names `deck.py` or
`SCHEMA.md` in a shipped skill. `shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates`
(gate decision) covers the `deck/` root spelling, not the files under it.
`engine-module-docstring-describes-pre-package-skill-layout` and
`installed-files-point-readers-at-a-deck-folder-install-never-creates` (both
closed) removed the same residue from other surfaces. Not fixed through: it is
another instance of the doc-accuracy family, and the pull-card fix-through bar
excludes meta-fix instances. Gate none: the target of every edit is fixed by
what install writes.

## 2026-10-14T04:43:17Z — Closure

- **What changed**: `goc/templates/skills/deck/SKILL.md` "The deck layout" lists the deck-level `log.md` and `<title>/` instead of `SCHEMA.md`, `README.md` and `deck.py`; `deck/reference.md:57-58` names the `goc` CLI as the engine; `refine-deck/SKILL.md` Step 3 points at `Skill(card-schema)`'s `reference.md` § Adding new tags instead of a SCHEMA.md PR. Mirrors re-synced, OpenClaw re-ported.
- **Guards**: `tests/test_skill_template_deck_links.py` widened with `retired_files` (bans both names across the six skill trees and four project-state trees; fed the five pre-fix lines verbatim) and `DeckLayoutBlockTest` (holds every shipped deck skill's layout block to a real `goc install`). The layout check is beyond the original DoD and is recorded as a fifth box: it is the only guard that sees the phantom deck-root `README.md`, whose name a ban cannot cover. The meta card's own README already noted that a derive-from-tree guard is cheap here.
- **Verification**: reproduce.py exit 1 → 0. The new test file at the pre-fix commit `00ecc037` (scratch worktree) fails 7 times — 30 retired-name hits plus the layout check in all six trees; on the fix 15/15 pass. Size caps: deck 10,094 → 9,965 of 10,100; refine-deck 14,198 → 14,180 of 14,200.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1308 passed / 0 failed; `goc validate` exit 0; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` green
- **Deck**: doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them (gate decision) gets this instance's row and paragraph updated to closed. No open card describes this defect; ship-game-of-cards-as-cross-agent-cli names `deck.py` only as the historical engine it replaced.
- **Surfaced**: `goc/engine.py` still names both retired files — the quality-pass prompt sent to the model says the title antipatterns are the set "deck.py `new`" rejects, and the frontmatter-parser banner comment says it parses SCHEMA.md, while `load_schema` reads `schema.yaml` through yaml_lite. Outside this card's skill-template scope; filed separately.

## Closure verification (2026-10-14T04:43:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-14 — Closure' present

## 2026-10-14T04:46:13Z — Forward pointer

The engine residue named under **Surfaced** in the closure entry is filed as
`engine-still-names-the-deck-script-and-schema-file-goc-replaced` (9faaa750,
gate none, advancing the same doc-accuracy umbrella). README gained a
`## Follow-up` section pointing at it.
