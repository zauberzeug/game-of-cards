## 2026-08-24T05:09:56Z — Closure

- **What changed**: `.game-of-cards/deck/deck-fills-with-decision-gated-cards-faster-than-they-are-decided/reproduce.py:129-130`
  — the runway is now `len(goc_json("--ready"))` instead of
  `gates.get("none", 0)`; the gate count survives as an explicitly labelled
  upper-bound line (`:122`, `:137`) with a per-axis breakdown of the gap, and
  `goc_json()` (`:64`) passes `check=True` so a failed invocation raises
  rather than parsing an empty payload as zero cards. A falsifying
  `reproduce.py` lands in this card's directory.
- **Verification**: probe exits **1** against the pre-fix script (which printed
  `PASS: runway of 16 cards is above the 15-card floor` and exited **0** on a
  synthetic deck of 16 gate-free-but-unpullable cards) and **0** against the
  fixed one. On this repo's deck: gate-none upper bound **6**, runway
  **0** — the pre-fix script reported 6 as the runway. Control scenario:
  gate count 19, runway 3, tracked exactly.
- **Audit**: no rubric configured; mechanical fix. (For the record, the fix
  binds the repo's one-predicate-one-definition rule that
  `card_is_ready`'s own docstring states — this was the seventh hand-rolled
  copy — but `.game-of-cards/hooks/finish-card.md` defines no rubric.)
- **Sweep (DoD item 6)**: 439 deck `reproduce.py` files scanned; 10 touch
  `human_gate` outside a frontmatter fixture; **1 offender** (the target),
  **0 siblings**. Breakdown table in the README.
- **Project impact**: the parent card's DoD item 1 can no longer go green on a
  starved loop. Its `## What's broken` table, `## Empirical evidence` block
  and `log.md` are re-rendered from the fixed script; its parked decision,
  option set and recommendation are untouched.
- **Tests**: 1030 passed / 0 failed; `uv run goc validate` exit 0.

## Closure verification (2026-08-24T05:10:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-08-24 — Closure' present
