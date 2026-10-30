## 2026-10-30T05:05:32Z — Closure

- **What changed**: `goc/engine.py` — `frontmatter_copy_lines` and `validate_body_repeats_frontmatter` add the advisory `BODY_REPEATS_FRONTMATTER` class to `goc validate`. Outside fenced code blocks it reports a single-token `title:` / `human_gate:` line, a `definition_of_done:` block header, a method-tagged DoD item at the two-space block indent, or a repeat of the body's first H1. Terminal cards are checked too. `Skill(refine-deck)` gained the edit-the-body-only rule in its core and `reference.md` § Editing card bodies; its size cap went from 15,300 to 15,700 with the rationale in `tests/test_skill_body_size.py`. New `tests/test_validate_body_repeats_frontmatter.py` (12 tests).
- **Deck repairs** (the true positives DoD 2 anticipated): `block-scalar-parser-collapses-whitespace-only-content-lines` got its body back from e1eb3ece, after 83c1408d had dropped the H1 and leading sections. `next-card-reclassify-checklist-cites-nonexistent-docs-framework-path` had its proposed replacement DoD fenced. Each card's `log.md` records the edit.
- **Verification**: `reproduce.py` exits 0. Against the pre-fix engine (a temporary worktree at 46072321) it exits 1, with both spliced scratch cards passing silently, and the live-deck test flags both cards above. The check flags the 2026-08-24 incident body (two DoD lines and the repeated H1) and stays silent on its repaired version. First deck run: 2 of 823 cards flagged; after the repairs, 0.
- **Design notes**: the key set is narrowed to `title`, `human_gate` and `definition_of_done` with value-shaped lines, because a bare column-0 test over every schema key drew two wrapped-prose false positives (`status:`, `waiting_until:`). Only a repeated H1 counts, since a different second H1 is a legitimate layout. There is no line number in the message: the sibling advisory classes quote samples instead.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1444 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-10-30T05:05:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-30 — Closure' present
