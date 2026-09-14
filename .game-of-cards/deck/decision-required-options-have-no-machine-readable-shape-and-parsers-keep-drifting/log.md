## 2026-09-14 — refine-deck: orphaned meta-fix family wired

Surfaced by Step 2's meta-fix zero-edge sub-check: this umbrella's body
declares "This card is the root; these are its known instances" and
names four cards, but carried `advances: []` / `advanced_by: []`. Filed
2026-07-26, i.e. after the pass that wired the earlier umbrellas
(`meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired`,
closed 2026-06-21), so this is a new unwired umbrella rather than a
regression of that work.

Wired per the established convention — sibling `advances` umbrella,
umbrella `advanced_by` siblings, set atomically by
`goc advance <umbrella> --by <sibling>`:

- decide-misparses-fenced-double-hash-line-as-decision-section-terminator (open)
- goc-decide-leaves-prior-decision-block-when-the-body-already-has-one (open)
- decide-card-rephrases-and-reorders-the-cards-own-options (closed)
- decision-verdict-coherence-check-skips-rubric-derived-decision-headings (closed)

Left deliberately UNwired: `dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting`,
which the body names as "sibling in kind, different subject" — a peer
umbrella, not a family member, and the closed wiring card is explicit
that peer cross-references must not become family edges.
