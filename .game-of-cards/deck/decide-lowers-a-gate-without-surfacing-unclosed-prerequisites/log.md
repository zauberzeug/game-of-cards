## 2026-07-26: filed from a live instance in this repo

Filed after a decision was recorded on
[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
without reading its `advanced_by` prerequisite, which corrected the very
premise being decided. The decision was rewound the same day.

Filed as an engine gap rather than as a process note because `goc decide`
already parsed the frontmatter carrying the edge and chose to print
nothing about it, while the queue and board renderers print a dependency
advisory for the same condition. The asymmetry is the defect: the surface
that *removes* the human gate is quieter about prerequisites than the
surfaces that merely list the card.

Deduped before filing. Three neighbours were checked and none covers this:

- `advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`
  (closed 2026-05-26) settled edge *semantics* — ~80% value contribution,
  ~20% strict, distinction "carried by the body, not the field." That
  decision is what makes this advisory necessary rather than redundant:
  since the field cannot express strictness, the only way to tell is to
  read the prerequisite, and nothing prompts that at decide time. No
  change to closure or readiness semantics is proposed here.
- `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`
  (done) covers gate *lowering* on terminal cards — a different invariant.
- The missing gate-*raise* verb, which this instance also hit (the rewind
  required hand-editing frontmatter), is already a DoD item on
  `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`.
  Connected there rather than re-filed.

Scaffolded at `--gate none` deliberately. The one design question —
advisory or blocking — is answered by two existing constraints rather
than by taste: refusing would break the ~80% loose-edge majority the root
card settled, and the deck's house style for anything short of a schema
violation is warning-only (`UNTAGGED_DOD_ITEM` and every other
`BlockerWarning` class). The DoD pins the advisory as non-blocking with
an unchanged exit code so a later pass cannot quietly harden it.

`reproduce.py` exits 1 on `main`; output pasted verbatim into the README.
