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
