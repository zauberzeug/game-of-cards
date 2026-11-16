## 2026-11-16T02:25:00Z — Filed by refine-deck

Surfaced by the 2026-11-16 hygiene pass. Its tag sweep scored the `bug`
state row over the live deck and found 11 open `meta-fix` umbrellas carrying
`bug` while their two or more wired instances meet the `epic` row. The
regression test reads `not epic` as "does not carry the `epic` tag", under
which all 11 pass; the reference reads the axes as orthogonal, under which
the clause should not exist. The sweep reports and never strips, so no tag
was touched; this card files the contradiction behind the report.

Dedup: `story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it`
reconciled the `story` row with the same paragraph and left the `bug` row as
it was; no open card names the `bug` row. Filed at `human_gate: none` with a
recommended fix because the run that filed it had no human in the loop; a
reader may raise the gate if the alternative deserves a decision.
