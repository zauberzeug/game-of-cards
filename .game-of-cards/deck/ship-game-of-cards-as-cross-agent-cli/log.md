## 2026-05-03: decision recorded

Approve scope as drafted: six sub-cards in package → install → AGENTS.md → bootstrap → multi-agent-shim → dogfood-migrate sequence — the six-sub-card decomposition mirrors the niche standard (Spec-Kit, BMAD, Agent OS, Ruler) and the dogfood migration on phasor-agents is the integration test that proves the whole epic; sub-card-level gates (v1 agent set, cutover timing) get decided independently when their cards are pulled. Gate decision → none.

## 2026-05-04 — Gate raised to session

Autonomous pull skipped direct epic work. The epic still depends on
`write-agentsmd-alongside-claudemd` (session-gated), the open bootstrap UX
card, PyPI/external-repo verification, and the phasor-agents dogfood migration.
Those are release/session decisions rather than a single pullable code patch,
so the parent epic is parked at `human_gate: session` until that coordinated
release pass happens.

## 2026-07-13 — Deck hygiene pass

Stale-open review (60d+ without log activity): lead still real — 18 children advance this epic and several remain open. Card is `human_gate: session` by design; no status change. Staleness clock reset.

## 2026-10-22T05:13:40Z: decision recorded

Close as done: 15 of 18 children are closed, the maintainer confirmed DoD 6/7 (phasor-agents and an external repo run goc end-to-end), DoD 8 is struck as superseded by the personas positioning, and the three open roadmap children are detached and stay parked — The maintainer decided in a human session on 2026-10-22; the ship-v1 scope is delivered, and the open children are roadmap design sessions rather than shipping work. Gate session → none.

## 2026-10-22T05:14:11Z — Closure

- **What changed**: no code — DoD 1–5 ticked against their closed sub-cards, DoD 6–7 ticked on the maintainer's confirmation in the 2026-10-22 human session, DoD 8 struck as superseded by `define-personas-and-use-cases-for-game-of-cards`. The three open roadmap children were detached with `goc unadvance` (ccbe5d99, c972ca93, f5cc4e43) and stay parked on their own; an "## Outcome" section records the result.
- **Verification**: PyPI lists 27 releases 0.0.1–0.0.27; all remaining `advanced_by` cards closed; `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: the ship-v1 epic stops sitting at the top of the gated queue (value 9.0) as if v1 had not shipped.
- **Tests**: no code touched; the full suite runs at the end of this batch.

## Closure verification (2026-10-22T05:14:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 15 closed
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
