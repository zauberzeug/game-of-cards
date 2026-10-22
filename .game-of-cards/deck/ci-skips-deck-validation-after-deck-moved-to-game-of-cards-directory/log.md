## 2026-05-27T00:00:00Z — Parked: requires maintainer with `workflows` permission

The autonomous drain bot pulled this card, implemented the documented fix,
and verified it:

- `.github/workflows/ci.yml` "Validate deck" step rewritten to guard on
  `[ -d .game-of-cards/deck ] || [ -d deck ]` (was `[ -d deck ]`).
- Stale ci.yml header comment refreshed (skill count 11→every; deck path).
- AGENTS.md "No pytest suite exists yet" line corrected to describe the
  real `tests/` regression suite CI already runs.
- Verification: reproduce.py exit 0; `uv run goc validate` clean;
  `scripts/sync_plugin_assets.py --check` clean.

**Push blocked.** `git push origin main` was rejected:

```
! [remote rejected] main -> main (refusing to allow a GitHub App to
create or update workflow `.github/workflows/ci.yml` without
`workflows` permission)
```

The bot's GitHub App token cannot push changes to `.github/workflows/`
(documented in AGENTS.md). Leaving the commit on local `main` would
block every subsequent bot push (each would re-include the unpushable
workflow commit), so the bot reset its two local commits and reverted
the ci.yml + AGENTS.md edits from the working tree. The exact fix is
preserved in the card body's "## Fix" section and the "## Handoff
required" note.

Parked at `human_gate: session`. A maintainer with `workflows` push
permission should apply the documented diff and push.

## 2026-10-22T05:07:53Z: decision recorded

Apply the documented ci.yml fix from a human session: guard the validate step on .game-of-cards/deck with the legacy deck/ fallback and refresh the stale header comment — The maintainer approved it in a human session on 2026-10-22; the fix was fully specified and only needed a human commit, since the bot token cannot push .github/workflows/. Gate session → none.

## 2026-10-22T05:09:05Z — Closure

- **What changed**: `.github/workflows/ci.yml` — the "Validate deck" step guards on `[ -d .game-of-cards/deck ] || [ -d deck ]` (was `[ -d deck ]`), and the header comment drops the stale "All 11 skill templates" / root `deck/` wording. Applied from a human session (the bot token cannot push workflow files).
- **Verification**: `reproduce.py` → "RESULT: OK — CI deck-validate guard resolves to the canonical deck", exit 0; `uv run goc validate` exit 0 on 811 cards; `ci.yml` parses as YAML.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: CI validates the real deck again on every push and PR; it had been skipped since the deck move, which let a summary-less card keep main red from 2026-08-13 until 494291ff.
- **Tests**: no code touched; the full suite (1339 passed / 0 failed) last ran at af6ce90d and runs again at the end of this batch.
- **Struck**: DoD 4 (AGENTS.md "No pytest suite" line) — moot since 99c58114.

## Closure verification (2026-10-22T05:09:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
