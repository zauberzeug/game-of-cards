## 2026-06-15T04:04:07Z — Post-close amendment

This card's principle — autonomous CI should pass a floating tier alias
(`opus`), not a pinned model ID — was re-violated and then re-vindicated:

- **Re-violated** by [`agent-workflows-pin-opus-instead-of-latest-fable-5-model`](../agent-workflows-pin-opus-instead-of-latest-fable-5-model/)
  (2026-06-10), which pinned the specific ID `claude-fable-5` to chase a
  tier above Opus. It referenced neither principle card, so the
  "float, don't pin" decision was invisible at the moment it was undone.
- **Re-vindicated** by [`pin-autonomous-workflows-to-opus-while-fable-5-disabled`](../pin-autonomous-workflows-to-opus-while-fable-5-disabled/)
  (2026-06-15): `claude-fable-5` was disabled, the pinned runs would have
  stalled, and the fix was to float back to `opus`.

Recurring failure mode: when a stronger model ships in a *new tier*
(Opus → Fable), there is no floating alias for "absolute strongest across
tiers" (no `latest`), so the upgrade tempts a specific-ID pin — which
re-introduces exactly the staleness/availability fragility this card
resolved. The durable move is to pin only when a cross-tier jump is worth
the fragility, and to revert to the tier alias the moment that ID is
deprecated or disabled.
