## 2026-05-29T14:01:25Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible fix paths. Pick one before any engine edit lands.

**Option A — Refuse-and-redirect (symmetric with `_cmd_decide`).**
`_cmd_done`, `_cmd_done_bundle`, and `_cmd_status` refuse when `human_gate != "none"` and tell the operator to run `goc decide` first. Validator adds the `status in TERMINAL_STATUSES ⇒ human_gate == "none"` invariant. Strongest contract — terminal closure is gated on a recorded decision/session resolution — but blocks scripted bulk-close flows that haven't been gate-aware.

**Option B — Auto-lower on close.**
The four close paths silently write `human_gate: none` when flipping to a terminal status. Validator adds the same invariant. Lowest operator friction but discards the gate's signal at exactly the moment its history would be most useful, and conflicts with the existing `goc decide` design that *records* the decision in `log.md` before lowering the gate.

**Option C — Validator-only.**
Leave the close verbs alone; have `validate_card` flag terminal-but-gated cards so the contradiction is loud at CI time, and let operators decide repair on a case-by-case basis. Cheapest fix but leaves the bug latent in fresh decks until the next `goc validate` runs.

**Recommendation:** Option A. It preserves the decide ↔ close symmetry the codebase already commits to (line 4557 refuses one direction; the four close paths should refuse the other), and the validator addition makes the invariant a catalog-level fact rather than a per-command convention. The "scripted bulk-close" objection is hypothetical — no current bundle/status caller in tree expects to close a parked card.


## 2026-05-30T13:36:38Z: decision recorded

Refuse-and-redirect: the four terminal-close paths (goc done, done --bundle, status disproved, status superseded) refuse when human_gate != none and tell the operator to run goc decide first; validator adds the invariant status in TERMINAL_STATUSES implies human_gate == none — it preserves the decide-close symmetry the codebase already commits to (decide refuses gate==none; close should refuse gate!=none) and the validator addition makes the invariant a catalog-level fact rather than a per-command convention; the scripted bulk-close objection is hypothetical with no current caller expecting to close a parked card. Gate decision → none.

## 2026-05-30T14:16:09Z — Closure

- **What changed**: `goc/engine.py` `_cmd_done` (~3326), `_cmd_done_bundle` (~3408), `_cmd_status` terminal branch (~4090), and `validate_card` (~1283) all gain the symmetric guard: any terminal-status entry refuses (or in the validator's case, errors) when `human_gate != "none"`, with a message that points at `goc decide`.
- **Verification**: `uv run python .game-of-cards/deck/goc-done-marks-cards-done-without-clearing-or-checking-human-gate/reproduce.py` now exits non-zero (the `goc done` step exits 2, leaving `status: open` and the `## Decision required` body intact). `tests/test_close_terminal_gate_guard.py` adds 8 focused tests covering all four terminal entry points + validator (done, disproved, superseded). Migrated 7 historical closed cards from `human_gate: session` → `none` so the new validator invariant passes on this deck.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a (engine guard + validator invariant, no consumer-facing API change beyond the new refusal path).
- **Tests**: 307 passed / 0 failed / 0 xfailed.
- **Bundled with**: (none)

## Closure verification (2026-05-30T14:16:28Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
