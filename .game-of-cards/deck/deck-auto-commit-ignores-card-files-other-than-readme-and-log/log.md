## 2026-08-10 — second narrowness found in the same pathspec: it cannot express a removal

An audit pass reached this same comprehension from the other side. Besides
the hardcoded `("README.md", "log.md")` pair this card is about, the
pathspec also filters on `.exists()` (`goc/engine.py:4677-4682`), so a
deleted file can never enter it — and since the commit that follows is
pathspec-scoped, no goc verb can commit a deck-file removal at all.
`goc move` reaches it: `git mv` stages the source-side deletion, nothing
commits it, and the next auto-committing verb publishes the renamed card
while the old one stays in HEAD. Every clone then holds two copies of the
card and `goc validate` reports both OK.

Measured in
[card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck](../card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck/),
wired as `advances` — this card is its prerequisite, because both
narrownesses are settled by the one open question here.

The connection changes the option weighting, so the README's "Decision
required" section is updated in place. Verified on git 2.54 rather than
assumed: a directory pathspec (`git add -- <dir>` + `git commit -- <dir>`)
carries a deletion inside that directory with no `-A` needed, while a
pathspec naming only surviving files leaves the removed path in HEAD. So
Options A and C fix both narrownesses for free and Option B does not —
an extension allowlist is still a list of paths that must exist.
