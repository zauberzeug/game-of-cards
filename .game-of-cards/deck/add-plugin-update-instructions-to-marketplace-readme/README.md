---
title: add-plugin-update-instructions-to-marketplace-readme
summary: "The marketplace listing's README is `claude-plugin/README.md` (added 2026-05-08 in `add-readme-to-claude-code-plugin`). It documents the first install (`/plugin marketplace add`) but not the update path. Claude Code's `/plugin install` reuses the local marketplace clone and does not refresh it automatically — so a user who installed the plugin once and reinstalls after a new commit silently gets the stale bytes (the same UX wall the closed card `plugin-install-doesnt-refresh-stale-marketplace-cache` documented in `site/llms.txt` and the `kickoff` skill body, but never propagated into the new plugin README). Surfaced today during Rodja's pre-submission smoke test: the running plugin still showed the old `bootstrap` skill name even after a reinstall, and only `/plugin marketplace update` recovered the renamed skills. Add an 'Updating an existing install' block to `claude-plugin/README.md` mirroring the wording in `site/llms.txt`. Also clean up `site/llms.txt`'s post-install example which still tells users to type `/bootstrap` (the pre-rename skill name) — should be `/kickoff`."
status: done
stage: null
contribution: low
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - plugin-install-doesnt-refresh-stale-marketplace-cache
  - align-skill-names-with-agile-vocabulary
tags: [bug, documentation]
definition_of_done: |
  - [x] `claude-plugin/README.md` has an "Updating an existing install" section between "Install" and "First use" that explains why `/plugin install` alone is not enough after a new commit, gives the canonical `/plugin marketplace update` + `/plugin install` sequence, and shows the `marketplace remove` + `add` round-trip as a fallback if `update` is not available — wording consistent with the equivalent block in `site/llms.txt`
  - [x] `site/llms.txt` post-install example uses the current skill name (`/kickoff`, not `/bootstrap`) so the homepage docs and the marketplace README agree on what to type first
  - [x] No `bootstrap` slash-command or `/bootstrap` substring remains in `site/llms.txt` or `claude-plugin/README.md` (other matches outside these two files are out of scope; the prior card already swept the workflow + script callers)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Add update instructions to the marketplace README

## Why

The Claude Code plugin marketplace install is a *clone-once* relationship:
running `/plugin marketplace add zauberzeug/game-of-cards` clones the repo
to `~/.claude/plugins/marketplaces/...` and subsequent
`/plugin install game-of-cards@game-of-cards` calls install from that
cached clone. Claude Code does NOT refresh the clone on
`uninstall`+`install`, so any consumer updating to a newer plugin version
silently gets old bytes unless they explicitly run
`/plugin marketplace update <name>` (or `remove`+`add`) first.

This was already documented in `site/llms.txt` (added by the closed card
`plugin-install-doesnt-refresh-stale-marketplace-cache`, 2026-05-07) and
in the `kickoff` skill body. But the plugin README that ships *with* the
plugin payload (and that the marketplace listing itself will display when
the submission lands) is `claude-plugin/README.md`, which was added today
in a separate card (`add-readme-to-claude-code-plugin`) that did not
inherit the refresh-idiom guidance. So a fresh consumer browsing the
community marketplace and following the README's install instructions
will install fine the first time and hit the wall on the first update.

This card closes that gap before the marketplace submission goes out.

While editing consumer docs, also fix a small leftover from the skill
rename: `site/llms.txt` line 55 tells users to type `/bootstrap` after
install, which is the pre-rename skill name. Should be `/kickoff`. The
prior workflow-fix card swept CI and `goc.md`; this is the missed
straggler in the homepage docs.

## Out of scope

- Reorganizing the rest of `claude-plugin/README.md`. The just-landed
  README is intentionally short; this card adds one section, not a
  rewrite.
- Persuading Claude Code upstream to make `/plugin install`
  auto-refresh. The closed `plugin-install-doesnt-refresh-stale-
  marketplace-cache` card already attests that documenting the idiom
  is the interim treatment; a request to upstream is a separate ask
  not blocking this submission.
- A static-analysis tripwire that enforces "no skill names anywhere in
  consumer docs that are not in the current skill registry." The
  `release-smoke-references-renamed-skills-fails-dry-run` card noted
  this as a candidate; not filed here.

## Cross-references

- `add-readme-to-claude-code-plugin` (done 2026-05-08) — added the
  README this card extends.
- `plugin-install-doesnt-refresh-stale-marketplace-cache` (done
  2026-05-07) — original record of the cache-refresh UX wall;
  documented the idiom in `site/llms.txt` and `kickoff`.
- `align-skill-names-with-agile-vocabulary` (done 2026-05-08) — the
  rename whose sweep of `site/llms.txt` missed line 55.
- `list-game-of-cards-on-anthropic-community-marketplace` (open,
  gate=decision) — depends on this card for marketplace-submission-
  grade consumer docs.
