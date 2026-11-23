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

## 2026-11-16T02:03:00Z — Traceback frame restored

The body's dry-run traceback line (`ValueError: advanced_by: not a list`
at `engine.py:4954 → 4911`) is the frame chain a live run printed on
2026-06-23: a record, not a claim about where the code sits now. Every
hygiene pass from 2026-08-10 on renumbered its first frame (to `7165` by
2026-11-09) and left the second, so the line matched no run. Restored to the
filing-time `4954`.

## 2026-11-23T04:35:00Z — Quoted CLI results moved into a fence

The three "Live CLI confirmation" result bullets under `## Empirical
evidence` now sit in a fenced block, numbers as filed (`4954 → 4911`), with
the inline-code markup dropped and the wording otherwise unchanged. In prose
the citation pass's scope rule read the frame chain as a cite about where
the code lives now: four consecutive passes renumbered it before the
2026-11-16 restore, and the 2026-11-23 pass proposed the move again. Inside a
fence with no `#` or `//` marker before the cite, the marker test reads it
as a record, so no later pass has to recognise it by reading the line.
Rule and its history:
[citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose](../citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose/).
The defect this card describes and its gate are unchanged.
