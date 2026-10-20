## 2026-10-20T04:40:13Z — Sibling filed: the Pages deploy has the same blind spot

- **Finding**: `pages.yml` deploys on `push` (paths filter) or `workflow_dispatch` only, so bot pushes never start it either. Its most recent run is 2026-07-15. Nine `claude[bot]` commits to `README.md`, `goc.md`, `ABOUT.md` and `site/` are unpublished since then, eight of them closing doc-fix cards. Every live mirror on game-of-cards.com is byte-identical to the 2026-07-15 tree.
- **Filed as** `website-never-redeploys-after-bot-pushes-so-doc-fixes-stay-unpublished` (gate `session`). It is a separate card rather than evidence here: the consequence is different, and options A, B and D here would close this card while leaving the site frozen. Only option C fixes both.
- **Body change**: one paragraph added at the end of `## Decision required` pointing at the sibling. No option text changed and no decision recorded; the gate stays `session`.
