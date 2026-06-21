## 2026-06-21 — filed

Surfaced during an empty-queue audit pass. Confirmed reachable:
`_cmd_repair_edges` classifies half-edges as fixable/structural against the
single original snapshot in the dry-run loop (`engine.py:4941-4946`), while
the `--apply` loop reloads before each edge (`engine.py:4964-4977`). On a deck
where one repair adds the `advances` edge that closes a cycle for another,
the dry-run promises 2 repairs but `--apply` performs 1 and exits 1.
`reproduce.py` prints the divergence and exits 0.

Filed at `human_gate: none` (the local fix direction is determined: make the
dry-run loop simulate earlier same-run repairs), but recorded as the 4th
instance of the meta-fix family
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
via an `advances` edge — and the first instance outside the
install/upgrade/migrate cluster. Not fixed in this session: per the
fix-through rule, the Nth instance of a catalogued meta-fix family is filed
and connected, not inlined; the architectural decision lives on the root card.

## Closed 2026-06-21

Fixed. Both `_cmd_repair_edges` passes now route through one incremental
classifier, `_classify_half_edges`, which classifies each half-edge and then —
when fixable — simulates that repair against the shared in-memory `Card`
objects via `_simulate_repair` (mirroring `_mutate_pair`'s reverse-half add).
Subsequent cycle checks in the same pass therefore observe the forward edges
earlier repairs add, exactly as `--apply` did by re-loading from disk before
each edge. The dual-snapshot drift is gone: the dry-run's "would be repaired
(N)" set now equals what `--apply` writes, and an edge made structural by an
earlier same-run repair is surfaced in the preview too.

The `--apply` loop no longer reloads per edge or re-classifies; it consumes the
up-front `fixable` list and applies the (idempotent) reverse-half mutations, so
the two paths cannot diverge again.

- `reproduce.py` now exits 0 (parity holds); its exit polarity was flipped to
  the repo convention (zero = fixed).
- New regression `test_repair_edges_dry_run_matches_apply_on_interacting_half_edges`
  asserts dry-run/apply parity on the two interacting Type-β advances half-edges.
- Forward pointer / instance entry on the root meta-fix card updated from
  "open (unfixed)" to the landed fix.
- Full suite green (504 tests); plugin mirrors re-synced.
