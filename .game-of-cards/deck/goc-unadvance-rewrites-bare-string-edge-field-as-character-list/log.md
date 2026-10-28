## 2026-10-28T04:33:45Z — Staleness re-check

Re-checked after `goc-unadvance-claims-success-when-removing-a-non-existent-edge`
closed. The defect stands: `reproduce.py` still exits 1, because it calls
`_remove_from_list_field` directly and that helper was not touched.

What changed is the CLI path in `## Reachability path`. `_cmd_unadvance` now
reads both endpoints before `_mutate_pair` and refuses (exit 2, nothing
written) when neither lists the edge, reading a non-list value as naming
nothing. So an edge whose two halves are both bare strings is now refused
instead of corrupted. A single bare-string half whose counterpart lists the
edge in a real list still passes the guard and is still rewritten
character-by-character: with `alpha.advanced_by: beta` and
`beta.advances: [alpha]`, `goc unadvance alpha --by beta` exits 0 and leaves
`advanced_by: [b, e, t, a]` (both re-checked 2026-10-28).
