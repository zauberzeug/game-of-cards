## 2026-10-04T07:10:00Z — Filed

Surfaced while closing
`deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects`,
whose fix edited the same deck skill. Dedup: no open card names `deck.py` or
`SCHEMA.md` in a shipped skill. `shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates`
(gate decision) covers the `deck/` root spelling, not the files under it.
`engine-module-docstring-describes-pre-package-skill-layout` and
`installed-files-point-readers-at-a-deck-folder-install-never-creates` (both
closed) removed the same residue from other surfaces. Not fixed through: it is
another instance of the doc-accuracy family, and the pull-card fix-through bar
excludes meta-fix instances. Gate none: the target of every edit is fixed by
what install writes.
