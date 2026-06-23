# Log

## 2026-06-23 — filed (audit-deck)

Surfaced during an audit-deck hunt while the pull-card ready queue was empty
(all `human_gate: none` open cards carry an active `waiting_on` overlay).

Finding: `goc repair-edges` and `goc advance` crash with an uncaught
`ValueError` traceback on a bare-string inverse edge field — the exact
corruption `goc validate` flags and recommends `goc repair-edges --apply` to
fix. The half-edge detector (`find_half_edges`, engine.py:1691-1693) coerces a
non-list inverse field to `[]` and emits a half-edge; the repairer
(`_add_to_list_field`, engine.py:4910-4911) rejects that same shape with
`raise ValueError`, uncaught up through `_repair_edge_diff` /
`_cmd_repair_edges` / `_mutate_pair`.

Verified live (throwaway deck + `reproduce.py`): detector reports 1 half-edge
(`repair_title=card-b`, `repair_field=advanced_by`, `repair_value=card-a`);
repairer crashes with `ValueError: advanced_by: not a list` at
`engine.py:4911`. `goc advance card-b --by card-a` reproduces the same trace.

Filed at `human_gate: decision` (fix direction — coerce-and-repair vs
clean-error vs umbrella's shared helper — is a judgment call governed by the
umbrella card's approach choice). Wired `advances` →
`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
as a new instance of that family. NOT fix-through-eligible: it is the Nth
instance of an already-catalogued root-cause family with an existing umbrella,
and the fix has a taste call.

Distinct from siblings: `goc-unadvance-rewrites-bare-string-edge-field-as-character-list`
is the *remove* sibling silently corrupting the card-under-edit;
`render-json-emits-bare-string-edge-fields-as-json-strings-not-lists` is the
renderer; `goc-repair-edges-apply-leaves-edge-repairs-uncommitted` assumes
repair succeeds. This is the *add* sibling (`_add_to_list_field`) crashing the
repair tool on the endpoint card — a detector/repairer asymmetry.
