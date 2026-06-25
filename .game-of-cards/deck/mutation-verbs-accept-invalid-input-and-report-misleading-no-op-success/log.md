## 2026-06-25 — gate raised to `decision` (pull-card)

An autonomous pull-card pass pulled this epic (the only ready card) and
found it is not drainable autonomously: DoD item 1 is a shared-shape
API-contract taste call, and all eight `advanced_by` children carry
their own `human_gate: decision`. No project-local consultation hook is
defined (`.game-of-cards/hooks/pull-card.md` is empty), so per the
pull-card Andon contract the gate was raised to `decision` rather than
guessing the contract.

Added a `## Decision required` section recording the three candidate
shapes (strict-refuse exit 2 / exit-0 stderr WARNING / honest no-op
success line) plus the factoring sub-decision, and surfaced the strong
codebase-internal default: `_cmd_advance` already strict-refuses the
self-target and cycle cases (`engine.py:5233`, `:5237`) and the engine
uniformly uses `goc: error: …` + `sys.exit(2)` for invalid input
(`:2496`, `:2510`, `:3437`, …). Recommended strict-refuse so the
shared-shape decision is a quick confirmation, not an open design space.

No code changed. The eight children remain open; this epic is parked
awaiting the shared-shape decision.
