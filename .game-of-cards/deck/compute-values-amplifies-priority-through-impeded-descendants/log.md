# Log

## 2026-05-26 — Decision: exclude impeded (`waiting_on`) descendants from scheduler value

**Decision:** a descendant carrying an active impediment overlay
(`waiting_impedes` is True — a `waiting_on` reason, or a future
`waiting_until`) does NOT contribute to a card's `compute_values`
scheduling score, for the full duration of its wait. `value_for` skips
it in the `advances` walk, exactly as it already skips terminal-status
descendants.

**Rationale:** the deck-as-scheduler-vs-record contract in `AGENTS.md`
states the scheduler axis walks `advances` edges across *live, workable*
cards. An impeded descendant is deliberately hidden from the pull queue
by `card_is_ready` → `waiting_impedes` (`engine.py:1617`); for scheduling
purposes it is exactly as un-pullable as a terminal descendant until its
wait resolves. Letting it amplify an ancestor's GRPW priority is the same
distortion the terminal-prune precedent
([compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/),
done) removed — re-introduced for the impediment axis the blocked-status
redesign added. The two guards (queue visibility and value math) are now
consistent.

This decision applies uniformly to all three impediment reasons
(`external`, `resource`, `deferred`). The card body raised whether a
`deferred` (deliberate postponement) descendant should perhaps still bias
priority. It should not: while the overlay is active the descendant is
un-pullable, so biasing the ancestor would rank a live card above its
peers on the strength of work nobody can start. The prune is
self-clearing — when a `deferred` card's `waiting_until` elapses (or its
overlay is cleared) it re-enters both the queue and the value walk on the
next recompute, restoring the amplification with no manual action. No
reason-specific exception is warranted.

**Implementation:** `goc/engine.py` `value_for` (in `compute_values`)
skips a descendant when `dest_card.status in TERMINAL_STATUSES or
waiting_impedes(dest_card)`. The docstring states the
live-AND-workable rule explicitly. `reproduce.py` asserts the impeded
case collapses to bare rank while the workable case still amplifies.

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `value_for` (in `compute_values`) — skip a descendant when `waiting_impedes(dest_card)` is True, alongside the existing terminal-status prune, so an impeded-and-queue-hidden descendant no longer amplifies a live ancestor's GRPW value. Docstring states the live-AND-workable rule.
- **Verification**: reproduce.py exits 0 — impeded B (waiting_until 2027) collapses A.value 7.3 → 1.0 (matching the terminal case); workable open B still amplifies A to 7.3.
- **Audit**: PASS — invokes the deck-as-scheduler-vs-record contract (AGENTS.md): scheduler axis walks `advances` across live, workable cards only; the impediment prune mirrors the terminal prune precedent.
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py passes; `goc validate` clean (pre-existing UNTAGGED_DOD_ITEM warnings on other cards only); plugin mirrors synced.
- **Bundled with**: none

## Closure verification (2026-05-26T23:46:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
