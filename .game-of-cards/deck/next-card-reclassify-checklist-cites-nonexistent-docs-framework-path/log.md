## 2026-10-30T04:56:00Z — Proposed DoD fenced

Wrapped the body's "definition_of_done (replace after decision)" list in a code
fence, with the content unchanged. Unfenced, its five lines read as a frontmatter
DoD at the block indent, which the new `goc validate` warning
`BODY_REPEATS_FRONTMATTER` reports
(goc-validate-accepts-a-card-body-that-carries-a-second-copy-of-the-frontmatter).
The fence marks the list as the proposal it is. The decision and the gate are
untouched.

## 2026-11-09T01:58:37Z — Staleness re-check

As-filed anchors gone from HEAD: `next-card/SKILL.md:3` (`description: Pick
the highest-leverage open card to work on next. Read ...`), moved by
`2f1ba0a5`, which quoted the description; it is still line 3.
Reproducer: none.
Verdict: not verified (no reproducer) — needs a human re-read. By reading, the
`docs/framework/*.md` bullet still ships at
`goc/templates/skills/next-card/SKILL.md:124` and in all five mirrors.
Not rewritten: `next-card/SKILL.md:3,25,50,51,102` restates the audit
catalogue's own row (`audit_catalogue.md:166`), numbered against the
pre-extraction file, so it is a record; left as is.
Gate unchanged.
