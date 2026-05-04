# goc-write-agentsmd-alongside-claudemd log

## 2026-05-04 — implementation shipped (4/6 DoD)

Goc-side commit `df473f7` in `~/Projects/game-of-cards`:

- **`goc/templates/AGENTS_GOC.md`** (new, 3.7 KB) — agent-agnostic GoC briefing. Three modes (session / autonomous / Andon-cord), CLI verb table, deck philosophy. Zero `Skill(...)` notation as instructions; one cross-link to CLAUDE.md noting that the Skill family is documented there.
- **`goc/templates/CLAUDE_GOC.md`** (slimmed from 5.0 KB → 2.0 KB) — Claude-specific delta only: 11 Skill names + the UserPromptSubmit silent-runtime hook. Cross-links to AGENTS.md for the shared briefing.
- **`install.py`** — `_append_marker_block` factored out (was `_append_claude_md_block`); now parameterized by `header` for the file-creation case. New `_sync_methodology_blocks()` writes both AGENTS.md and CLAUDE.md with identical marker brackets. Same upgrade re-sync logic for both.

### Smoke tests (all green)

1. Fresh tmpdir → `goc install` → AGENTS.md and CLAUDE.md both written with marker blocks.
2. Round-trip: `goc new agents-md-roundtrip` → tick DoD → `goc done` → `goc validate` OK.
3. Marker merge: pre-existing AGENTS.md with user content ("Bob") survives `goc install` (block appended below user content); survives `goc upgrade` re-sync (block replaced, user content preserved).
4. Plan grew from 29 → 30 writes (one new append for AGENTS.md).

### Why card stays open at gate=session

DoD-4 ("validated on 3 agent runtimes") and DoD-6 ("OpenCode round-trip with no CLAUDE.md") require sessions in OpenCode / Codex / Cursor / Copilot — runtimes I cannot drive from this Claude Code session. The implementation is correct *by construction* (no Claude-specific instructions in AGENTS.md; marker-bounded merge tested) but empirical cross-runtime verification needs a human session.

The pull-card cron will skip this card (gate=session) until a human runs the validation pass and either ticks the boxes via `goc decide` (lowering the gate) or files a follow-up validation card.

## /mindset audit

PASS — no axiom touched. Pure infra: markdown template authoring + idempotent file-merge logic. No bio-faithfulness or framework derivation.
