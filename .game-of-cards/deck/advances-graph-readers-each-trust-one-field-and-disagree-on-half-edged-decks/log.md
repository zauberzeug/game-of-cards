## 2026-11-09T04:31:01Z — Docstring quote under What's broken replaced

[cascade-root-warning-counts-only-cards-in-the-retired-blocked-status](../cascade-root-warning-counts-only-cards-in-the-retired-blocked-status/)
rewrote the `validate_blocker_coherence` docstring. Its CASCADE_CHAIN_ROOT
entry now describes the walk by the `advanced_by` edges it reads, so the
quoted line no longer showed a docstring naming the other field. The
README now shows the walk's adjacency build alone. The walk itself still
reads one half only, so the split this card describes is unchanged, as are
its options and recommendation.
