# Log

## 2026-06-25 — 6th family instance wired in

Closed [emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields](../emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields/)
added as `advanced_by`. It is the chomp-*indicator* face of this same
emit/parse mirror-drift: `_emit_block_field` selected only `|` (clip) and
`|-` (strip), never `|+` (keep), so a value ending in a trailing blank line
lost it on re-emit even though `_parse_block_scalar` already supported keep.
Patched one more edge case in isolation rather than from a shared contract —
which is exactly the recurrence this root tracks. The decision DoD's "indicator
decision … share one contract" item already anticipates this dimension; the
unified mechanism must subsume chomp selection too, not just whitespace-line
handling.
