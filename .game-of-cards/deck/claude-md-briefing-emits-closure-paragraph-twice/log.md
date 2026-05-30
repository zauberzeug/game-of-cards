# log

## 2026-05-30 — fix: removed duplicate paragraph from CLAUDE_GOC.md

Chose the **mechanical content fix** (option A from the card body) over
the alternative of teaching `_briefing_body` to dedup paragraphs between
the two templates.

Removed lines 15-19 of `goc/templates/CLAUDE_GOC.md` — the
"Closure is not frozenness" paragraph — because it is generic
methodology guidance (it never mentions Claude Code or any host-specific
surface), so its presence in `CLAUDE_GOC.md` violated the
"Claude-specific extras" contract documented in `_briefing_body`'s own
docstring. The AGENTS_GOC.md copy remains the single source of truth
for that paragraph; `_briefing_body` now concatenates the two templates
without any duplicated content for the CLAUDE.md sole-home target.

Why mechanical over dedup engine: the contract that CLAUDE_GOC.md
contains only Claude-specific extras is already documented; a single
known overlap doesn't justify a dedup pass that would silently mask
future drift. A targeted content fix is cheaper and aligns the file
with its stated purpose.

Regression coverage: `tests/test_briefing_body_dedup.py` exercises
`_briefing_body` across all three briefing targets (AGENTS.md /
CLAUDE.md / CLAUDE.local.md) and asserts the `Closure is not frozenness`
paragraph appears exactly once in each. `reproduce.py` now exits 0.

## 2026-05-30T01:07:14Z — Closure

- **What changed**: `goc/templates/CLAUDE_GOC.md:15-19` — removed the
  duplicate "Closure is not frozenness" paragraph; CLAUDE_GOC.md now
  carries only truly Claude-specific content (plugin install + kickoff
  handoff). AGENTS_GOC.md remains the single source of truth for the
  generic methodology paragraph.
- **Verification**: `reproduce.py` exits 0; `_briefing_body` emits the
  paragraph exactly 1 time in each of the three briefing targets
  (AGENTS.md / CLAUDE.md / CLAUDE.local.md).
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 241 passed / 0 failed / 0 xfailed (incl. new
  `tests/test_briefing_body_dedup.py`).
- **Bundled with**: —

## Closure verification (2026-05-30T01:07:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
