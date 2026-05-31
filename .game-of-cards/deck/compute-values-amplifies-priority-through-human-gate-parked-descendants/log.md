# Log

## 2026-05-31 — Decision: exclude `human_gate`-parked descendants from scheduler value

**Decision:** a descendant carrying `human_gate: decision` or
`human_gate: session` does NOT contribute to a card's `compute_values`
scheduling score for the duration of its gate. `value_for` skips it in
the `advances` walk, exactly as it already skips terminal-status and
`waiting_impedes` descendants. The `sort_default.live_direct` tiebreak
applies the same skip.

**Rationale:** the deck-as-scheduler-vs-record contract in `AGENTS.md`
states the scheduler axis walks `advances` edges across *live, workable*
cards. The composite ready-to-pull predicate `card_is_ready`
(`engine.py:1929`) hides a card from the queue on three independent
axes: terminal `status`, `waiting_impedes`, and `human_gate != "none"`.
The terminal axis was pruned from the scheduler walk by
[compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/);
the impediment axis followed in
[compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/).
The `human_gate` axis is the third — and last — `card_is_ready` gate the
prune was not yet mirroring. Letting it amplify an ancestor's GRPW
priority is exactly the distortion the two prior precedents removed:
ranking a live card above its peers on the strength of work nobody can
pull. The two guards (queue visibility and value math) are now
consistent across all three axes.

The duration counter-reading raised in the card body ("human gates
resolve in hours, impediments in months, so amplification through a
gate is still useful") does not survive: an autonomous puller invoked
while a gated chain exists sees its leverage line distorted toward the
gated chain *right now*, but the gate may be lowered later or never. The
scheduler decision must be based on present pullability, not expected
gate-resolution latency — the same argument that defeated a
reason-specific exception for `deferred` impediments in the prior
precedent. The prune is self-clearing: when the gate is lowered via
`Skill(decide-card)`, the descendant re-enters the walk on the next
recompute with no manual action, restoring the amplification.

This decision applies uniformly to both gate kinds (`decision` and
`session`). The leverage-line Andon advisory at
`render_leverage_line` (`engine.py:2434`) remains the human-facing
escalation signal for high-value gated cards; it consults the
*post-prune* values for live cards but compares them against gated
cards' own values (which still reflect their own contribution rank,
not the un-amplifiable amplification they could not pass through).

**Implementation:** `goc/engine.py` `value_for` (in `compute_values`)
and `sort_default.live_direct` both extend their existing prune
condition to include `dest.human_gate != "none"`. The `compute_values`
docstring states the predicate-aligned rule explicitly: the prune
mirrors every gate in `card_is_ready` except the `status == "open"`
clause (`active` descendants stay workable for the scheduler).
`reproduce.py` asserts the gated case (B at `human_gate: decision`)
collapses A.value to bare rank (3.0) — matching the impeded case — while
the ready case still amplifies to 9.3.

## 2026-05-31T00:00:00Z — Closure

- **What changed**: `goc/engine.py` — `value_for` (in `compute_values`)
  and `sort_default.live_direct` skip descendants for which
  `dest.human_gate != "none"`, alongside the existing terminal-status
  and `waiting_impedes` prunes. Docstrings extended to state the
  three-axis live-AND-workable rule. Plugin mirrors (`claude-plugin/`,
  `codex-plugin/`, `openclaw-plugin/`) regenerated.
- **Verification**: `reproduce.py` exits 0 — gated B
  (`human_gate: decision`) collapses A.value 9.3 → 3.0 (matching the
  impeded case); ready B still amplifies A to 9.3. `uv run python -m
  unittest discover -s tests` clean (346 passed). `uv run goc validate`
  clean.
- **Audit**: PASS — invokes the deck-as-scheduler-vs-record contract
  (AGENTS.md); the human-gate prune mirrors the two prior axis prunes
  (terminal, impediment) and aligns the scheduler walk with every gate
  in `card_is_ready`.
- **Project impact**: this repo's deck currently carries two
  `human_gate != none` active cards
  (`support-external-game-of-cards-state-location`,
  `list-game-of-cards-on-anthropic-community-marketplace`); any
  `advances` edge pointing at either will now correctly omit their
  contribution from the source card's GRPW value until the gate is
  lowered.
- **Tests**: `uv run python -m unittest discover -s tests` → 346 OK;
  reproduce.py exits 0; `uv run goc validate` clean; plugin mirrors
  synced.
- **Bundled with**: none
