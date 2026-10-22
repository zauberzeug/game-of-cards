# write-agentsmd-alongside-claudemd log

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

## 2026-07-13 — Deck hygiene pass

Stale-open review (60d+ without log activity): 4/6 DoD items already checked and all three children are wired. Likely closable in a short human session — the two open items are the remaining scope. `human_gate: session`; no status change.

## 2026-10-22T05:12:47Z: decision recorded

Close as done: production use on Claude Code, Codex and OpenClaw counts as the three-runtime validation; strike the OpenCode-specific round-trip item — The maintainer decided in a human session on 2026-10-22 that the runtimes the deck actually runs on are the validation that matters; OpenCode is not a supported target (OpenClaw, a different product, is). Gate session → none.

## 2026-10-22T05:13:07Z — Closure

- **What changed**: no code — DoD-4 ticked as amended by the 2026-10-22 decision (Claude Code, Codex and OpenClaw in production count as the three runtimes), DoD-6 (OpenCode-only round-trip) struck; the "Validation required" section now records the resolution.
- **Verification**: this repo's `CLAUDE.md` is exactly `@AGENTS.md`; `codex-plugin/` ships the Codex payload that reads AGENTS.md; `openclaw-plugin/` runs in a production deployment; `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: one fewer session-gated card; the AGENTS.md block stays the cross-runtime briefing.
- **Tests**: no code touched; the full suite runs at the end of this batch.

## Closure verification (2026-10-22T05:13:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 3 closed
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
