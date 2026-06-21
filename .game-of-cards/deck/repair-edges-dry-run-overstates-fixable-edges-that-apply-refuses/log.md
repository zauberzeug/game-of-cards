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
