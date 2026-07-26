## 2026-07-26T07:44:02Z — Closure

- **What changed**: `goc.md:87–111` + `goc.md:213` — the Claude and OpenClaw
  plugin sections rewritten from the pre-0.0.6 payload (symlinks into
  `goc/templates/`, separate `goc` CLI install, 11/13 skills, two hooks, an
  unresolved bootstrap limitation) to the shipped one (real byte-mirrored files,
  bundled engine + `bin/goc`, 16/16 skills, three hooks, guarded fences).
  `tests/test_guidance_accuracy.py` — new `GocMdPluginReferenceAccuracyTest`
  with six guards that derive truth from the tree instead of restating numbers.
- **Verification**: `reproduce.py` 7/7 `[ok]`, exit 0 (was 6 `[FAIL]`, exit 1).
  The six new guards fail 6/6 when pointed at the pre-fix `goc.md`
  (`git show aa3905c5:goc.md`) and pass 6/6 against the fixed file — the
  non-vacuity check.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is empty); doc-drift correction with a derived-from-tree regression guard.
- **Project impact**: n/a
- **Tests**: 771 passed / 0 failed / 0 xfailed. `goc validate` exit 0;
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` both
  clean (no template or mirror touched — `goc.md` is a root doc with no mirror).
- **Bundled with**: none

Scope note: a seventh stale claim surfaced while editing the section — the "What
the plugin provides" list named `SessionStart` and `UserPromptSubmit` but not the
`Stop` hook that `claude-plugin/hooks/hooks.json` has registered since the
pattern-generalization hook shipped. Same file, same section, same root cause
(the section was never revisited), so it was folded into this card rather than
filed separately; `reproduce.py` gained claim 7 and the guard set gained
`test_claude_provides_list_names_every_registered_hook`.

Sibling sweep: grepped `README.md`, `ABOUT.md`, `CONTRIBUTING.md`, `PERSONAS.md`,
`DECK_LOCATION.md`, `site/`, and the three plugin `README.md`s for the same
claims (`symlink`, "shells to the goc CLI", the skill counts,
`CLAUDE_SKILL_DIR`). No surface repeats them, so no sibling card was filed. The
website serves `goc.md` itself at `/goc/` (`.github/workflows/pages.yml:11`), so
the correction propagates on the next Pages build with no second edit.

## Closure verification (2026-07-26T07:44:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
