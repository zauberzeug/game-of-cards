## 2026-06-04T04:56:54Z — New supporting evidence (no status change)

While auditing the parser/emitter surface, surfaced a fresh data point
for this family that strengthens the case against approach C and is
recorded here rather than as a redundant per-consumer card:

`goc repair-edges` **crashes with an uncaught `ValueError: <field>: not
a list`** traceback — in both the dry-run diff path (`_repair_edge_diff`
→ `_add_to_list_field`) and the `--apply` path (`_cmd_repair_edges` →
`_mutate_pair` → `_add_to_list_field`) — whenever a detected half-edge's
repair target carries a bare-string scalar on the field being repaired.

Reproduction (clean temp deck): card A `advances: [card-b]`; card B
`advanced_by: card-a` (bare string). `goc repair-edges` prints the
half-edge header line, then:

```
ValueError: advanced_by: not a list
  File ".../goc/engine.py", in _add_to_list_field
    raise ValueError(f"{field}: not a list")
```

Why this matters for the decision: the body previously cited
`_add_to_list_field`'s `raise` as the guard the remove-path *lacks*.
This evidence shows that guard is itself a defect — it converts the
half-edge that sibling #6
(`repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string`)
taught `find_half_edges` to detect into a hard crash of the dedicated
repair verb. Two shipped fixes now contradict: detection says
"repairable," the repair path aborts. Approach A (load-time
normalize/reject) or B (shared `_field_as_list` coercion) closes this;
approach C does not. Body "Compare to the sibling `_add_to_list_field`"
paragraph amended to record this.

Not filed as a standalone card: it is the Nth instance of this
already-catalogued family with this meta-fix already open — per the
audit sibling-sweep rule, evidence belongs on the architectural card,
not a new per-consumer filing.

## 2026-06-08 — Eighth unguarded site (no status change)

An audit-deck sweep surfaced an eighth read-time consumer that
iterates the list-typed fields without an `isinstance(v, list)`
guard: the verbose (`-vv`) raw-dump loop in `render_table`
(`engine.py:2552-2556`), which does `list(v)` over every
`LIST_REL_FIELDS` value. On a card hand-edited to `advances:
some-card` (bare scalar), `goc --status open -vv` renders
`advances: ['s', 'o', 'm', 'e', '-', 'c', 'a', 'r', 'd']`.

Reproduced verbatim on 2026-06-08 by exercising the loop directly
against `LIST_REL_FIELDS`. Distinct from sibling #3
(`dependency-blockers-iterates-non-list-advanced-by-...`), which
patched the `dependency_blockers` "awaiting" line and the named
per-field renderers but not this raw-dump loop. Display-only (no
file corruption), so lower-impact than the mutating siblings, but
one more consumer in the family.

Body section "## An eighth unguarded site" and Option B's consumer
list amended to record it. Not filed as a standalone sibling card —
per the audit sibling-sweep rule, an Nth instance of an
already-catalogued family with the meta-fix already open belongs on
the architectural card, not a new per-consumer filing. Card stays at
`human_gate: decision` pending the A/B/C choice.
