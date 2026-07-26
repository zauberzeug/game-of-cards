
## 2026-07-26T08:25:00Z — Seventh instance connected (audit-deck round)

An audit pass on the same day this card was filed surfaced instance seven and
connected it here rather than filing a duplicate root:
[ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/)
(open, `contribution: low`, `human_gate: session`). Two of the shapes this card
enumerates, in one eleven-line comment block: a bare count in prose ("All 11
skill templates" — `ls -1d goc/templates/skills/*/ | wc -l` returns 18) and a
forward-looking promise naming `goc-install-command-scaffolds-repo`, a card title
that has never existed.

Body amended in place (dashboard rule): instance table extended, count corrected
six → seven, and a paragraph added on what the new instance changes.

**The substantive addition is a surface-coverage gap, not just a tally.** Option A
enumerates the doc surfaces to sweep — `AGENTS.md`, `goc.md`, `README.md`,
`ABOUT.md`, `CONTRIBUTING.md`, `DECK_LOCATION.md`, `PERSONAS.md`, `site/`, the
plugin READMEs, the skill bodies. Instance seven lives in a
`.github/workflows/*.yml` header comment, which is on none of them. Whichever
option is adopted, the surface definition needs to cover tree-restating prose
wherever it lives — workflow headers, module docstrings, config comments — not
only the `.md` set. No decision is recorded here; that remains the human's pick.
