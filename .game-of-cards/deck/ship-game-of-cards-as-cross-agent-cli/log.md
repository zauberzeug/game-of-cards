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
