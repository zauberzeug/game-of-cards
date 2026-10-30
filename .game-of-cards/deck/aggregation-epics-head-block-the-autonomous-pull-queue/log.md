## 2026-10-30: recurred with the mutation-verbs epic, parked with the same overlay stopgap

A pull-card pass pulled
`mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success`
as the top `--ready` card. Five of its nine children had closed and the
other four are each gated at `decision`, so the pass had nothing it could
do on the epic. It parked the epic with `goc wait --reason resource`,
without raising its gate, because the epic has no question of its own, and
it left the epic a `## Waiting` section saying to clear the overlay when
the last child closes.

That is the second deck instance of the head-block, after the two
`blocked`-removal epics this card was filed on, which have carried
`waiting_on: deferred` since 2026-05-29. Two more data points for the
decision:

- The stopgap leans on a hand step at the far end. Nothing clears the
  overlay when the roster turns terminal, so a forgotten clear hides an
  epic that has become closable.
- The two stopgaps use different reasons (`deferred`, `resource`), and no
  `waiting_on` value names "waiting on gated children". A sweep that later
  lifts these overlays cannot find them by reason alone.

Dashboard updated in place: the "observable right now" passage under
`## What's broken` now dates the 2026-05-26 snapshot, records the overlays,
and names the recurrence.
