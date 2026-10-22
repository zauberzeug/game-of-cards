---
title: website-never-redeploys-after-bot-pushes-so-doc-fixes-stay-unpublished
summary: "The Pages workflow that publishes game-of-cards.com triggers only on a push to main, and GitHub starts no workflow run for a push made with the default GITHUB_TOKEN, which is the credential the autonomous bot pushes with. So the site has not deployed since the last human push touching its paths on 2026-07-15: nine bot commits have changed README.md, goc.md, ABOUT.md and site/ since then, eight of them closing doc-fix cards as done, yet every live mirror is still byte-identical to the 2026-07-15 tree. Visitors, and the LLMs llms.txt is written for, are still told the ClawHub install is unpublished and shown a --no-harness install flag that goc install now rejects."
status: open
stage: null
contribution: high
created: "2026-10-20T04:37:14Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: a human picks the deploy mechanism in `## Decision required` and records it with `goc decide`, settled together with `autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing`, whose option C would also fix this card
  - [ ] MECHANICAL: the chosen mechanism landed. A `.github/workflows/` edit is human-only, because the bot's `GITHUB_TOKEN` cannot write there
  - [ ] TDD: `reproduce.py` exits zero — no published mirror lags `main` by more than 48 hours
  - [ ] EMPIRICAL: verified on a real bot push — a bot-authored commit that changes a site path reaches game-of-cards.com with no human push, and the Pages run URL is recorded in `log.md`. The one-off manual dispatch that clears the backlog does NOT satisfy this item
  - [ ] MECHANICAL: the `pages.yml` header comment states which events deploy the site, so the next reader does not assume every push to `main` does
  - [ ] PROCESS: `uv run goc validate` passes
---

# The website never redeploys after bot pushes, so doc fixes stay unpublished

## Location

- `.github/workflows/pages.yml:50-60` — the trigger block. A push to `main`
  that touches a site path, or a manual dispatch, and nothing else:

  ```yaml
  on:
    push:
      branches: [main]
      paths:
        - README.md
        - goc.md
        - ABOUT.md
        - assets/**
        - site/**
        - .github/workflows/pages.yml
    workflow_dispatch:
  ```

- `.github/workflows/pages.yml:5-15` — the publishing map: `site/index.html`
  → `/`, `README.md` → `/README.md` and `/index.md`, `goc.md` → `/goc/` and
  `/goc.md`, `ABOUT.md` → `/about/` and `/ABOUT.md`; `site/llms.txt` reaches
  `/llms.txt` through the verbatim `site/` copy.
- `.github/workflows/pull-card.yml:75` — `github_token: ${{ github.token }}`,
  plus the default `persist-credentials` on its checkout. The autonomous
  agent commits and pushes to `main` as `GITHUB_TOKEN`. `audit-deck.yml:53`
  and `refine-deck.yml:55` push the same way.

## What's broken

GitHub starts no new workflow run for an event caused by the default
`GITHUB_TOKEN`, except `workflow_dispatch` and `repository_dispatch`. AGENTS.md
already relies on that rule in its release section:

> No PAT is needed (`workflow_dispatch` is the documented exception to the
> rule that `GITHUB_TOKEN`-triggered events do not start new runs)

`pages.yml` deploys on `push`, which gets no exception. The autonomous bot
writes almost every commit on `main`, so **no doc fix the bot pushes ever
reaches the website**. The site moves only when a human push happens to touch
one of the six paths. The last one was on 2026-07-15.

Nothing reports this. The workflow header promises that the site serves those
files and that "LLMs can fetch the same content as plain text/markdown". A
doc-fix card is closed once the file on `main` reads correctly, and none of
those cards checks the published copy.

## Empirical evidence

`uv run python .game-of-cards/deck/website-never-redeploys-after-bot-pushes-so-doc-fixes-stay-unpublished/reproduce.py`
(2026-10-20) fetches every file `pages.yml` copies verbatim. For each one it
finds the commit on `main` whose version of the file matches the live bytes:

```
pages.yml trigger block (the only events that deploy the site):
  on:
    push:
      branches: [main]
      paths:
        - README.md
        - goc.md
        - ABOUT.md
        - assets/**
        - site/**
        - .github/workflows/pages.yml
    workflow_dispatch:

most recent Pages run: 2026-07-15T06:38:37Z (push, success) on 3e17e3b3

live mirror vs main (defect when the oldest unpublished change is > 48h old):
  /README.md    == README.md at f1bd886c (2026-05-18); 1 later commit(s) unpublished, oldest 17 days old [DEFECT]
  /goc.md       == goc.md at 3e17e3b3 (2026-07-15); 7 later commit(s) unpublished, oldest 86 days old [DEFECT]
  /ABOUT.md     == ABOUT.md at 2e8081a5 (2026-05-11); 2 later commit(s) unpublished, oldest 17 days old [DEFECT]
  /llms.txt     == site/llms.txt at 8c4db872 (2026-05-18); 3 later commit(s) unpublished, oldest 80 days old [DEFECT]
  /             == site/index.html at fa70e6ee (2026-05-14); 1 later commit(s) unpublished, oldest 13 days old [DEFECT]
  /privacy.html == main
  /styles.css   == main
  /stars.js     == main

commits on main whose content is not on the site: 9, authored by: claude[bot]
closed cards whose committed fix is not on the site:
  - cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships
  - llms-txt-still-presents-the-clawhub-install-as-unpublished
  - cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay
  - goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there
  - cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it
  - install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag
  - deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects
  - plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove

[DEFECT] 5 of 8 published mirrors lag main by more than 48h: pages.yml deploys only on push, and pushes made with the default GITHUB_TOKEN start no workflow run, so bot-authored doc fixes never reach game-of-cards.com.
```

All nine unpublished commits are by `claude[bot]`. The ninth (`27db384e`)
advances `codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine`
rather than closing a card. Every live mirror is byte-identical to the
deployed commit `3e17e3b3`. The three files that still match `main` have not
changed since then.

Here is what the live site still says, against what `main` says:

- **`/llms.txt`**, the file aimed at LLM ingestion, still reads "Once the
  plugin is published, install via ClawHub:" and "Until publish lands (tracked
  under `publish-openclaw-plugin`), build from source". Closing
  `llms-txt-still-presents-the-clawhub-install-as-unpublished` on 2026-08-01
  removed exactly those two lines from `site/llms.txt`.
- **`/about/` and `/ABOUT.md`** still document `--no-harness` as an install
  flag: "`--no-harness` installs project state and guidance only". That flag
  no longer exists:

  ```
  $ goc install --no-harness --dry-run
  goc install: error: unrecognized arguments: --no-harness      (exit 2)
  ```

- **`/goc/` and `/goc.md`** still list `blocked` as an ordinary
  `goc status` target. They predate the plugin-switch recipe, the
  vendored-to-plugin cleanup, and the plugin-payload corrections.
- **`/`**, the home page, does not list the Codex plugin, which `main`'s
  `site/index.html` presents as a delivery channel.

## Why it matters

The website is the front door for agent-driven adoption. The onboarding path
that `README.md:28-32` and the home page (`site/index.html:125-127`) both
advertise is a single prompt to the user's own agent: "look at
game-of-cards.com and use the method for development here". The agent then
reads the site. On that path it gets install guidance that is three months
stale and wrong in two places: a live channel described as unpublished, and a
flag that fails with exit 2.

It also makes "done" mean less for every documentation card whose readers see
the published site. Eight cards closed between 2026-07-26 and 2026-10-15
fixed text on `main` that nobody reading game-of-cards.com can see. Nothing in
the deck shows it, because their closure checks read the repo file, and the
repo file is correct. `llms-txt-still-presents-the-clawhub-install-as-unpublished`
names its target as "the file LLMs ingest", and the live copy of that file
has not changed.

It has the same root cause as
[autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)
but needs its own fix. That card's four options all restore CI, yet only its
option C (push with a PAT or App token) also restarts this workflow. Option A
runs the suite inside `pull-card.yml`, option B chains `ci.yml` alone through
`workflow_run`, and option D schedules `ci.yml`. Any of those three closes
that card and leaves the website frozen. The two decisions should be taken
together.

[pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order](../pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order/)
has an EMPIRICAL item, "after the next Pages deploy", that only a human push
can satisfy today. Its own fix edits `pages.yml`, which is on the paths
filter, so that commit would deploy. That is why no edge is wired.

## Decision required

Every durable fix is a `.github/workflows/` edit, which only a human can land.
The options differ in how fast the site follows `main`, whether they need a
credential, and whether they drift as bot workflows are added.

- **A — Schedule `pages.yml`.** Add a daily `schedule:` trigger beside the
  existing ones, e.g. shortly after the 04:13 UTC pull-card run:

  ```yaml
  # .github/workflows/pages.yml:50
  on:
    push: …                    # unchanged — a human push still deploys at once
    schedule:
      - cron: '43 5 * * *'
    workflow_dispatch:
  ```

  *Pros:* one line, no credential, and it works whoever pushed. It cannot
  drift when a bot workflow is added or renamed. *Cons:* the site may trail a
  bot fix by up to a day, and it runs a ~40 s idempotent redeploy on days
  when nothing changed.
- **B — Chain on the bot workflows with `workflow_run`.** `pages.yml` also
  triggers when `Pull Card`, `Audit Deck` or `Refine Deck` completes. Those
  events come from the Actions service, not from the pushing credential.

  ```yaml
    workflow_run:
      workflows: [Pull Card, Audit Deck, Refine Deck]
      types: [completed]
  ```

  *Pros:* the site follows a bot fix within minutes, with no credential.
  *Cons:* it lists the bot workflows by display name, so a new or renamed one
  drops out without warning. It redeploys after every run, including the many
  that change no site path, unless a guard step is added.
- **C — Dispatch from inside the bot workflows.** After the agent step, run
  `gh workflow run pages.yml` when `git diff --quiet <start-sha> HEAD -- README.md goc.md ABOUT.md site assets`
  reports a change. `pull-card.yml:24-29` already grants `actions: write` for
  its own self-trigger. `audit-deck.yml:19-23` and `refine-deck.yml:21-25` do
  not, so both need it. *Pros:* it deploys exactly when a bot run changed the
  site, right after the push. *Cons:* three workflows to edit and keep in
  step, and the same drift as B for any future bot workflow.
- **D — Settle it through the CI card's option C.** Push with a PAT or GitHub
  App token, so every `push` trigger fires again, this one included, and
  `pages.yml` needs no change. *Pros:* one change fixes both cards and makes
  the workflow header true as written. *Cons:* it adds the long-lived write
  credential this repo has avoided so far: the release flow is OIDC-only, and
  AGENTS.md records that a `CLAWHUB_TOKEN` secret breaks releases. And if the
  CI card picks anything other than its option C, this card is still open.

**Recommendation: A.** It is the smallest change and needs no credential.
It is the only option whose coverage does not depend on keeping a list of
bot workflows current. If the CI card lands on its option C, D is free and A
becomes redundant but harmless.

Whatever is picked, the backlog does not have to wait for it. One
`gh workflow run pages.yml` publishes current `main` today; `workflow_dispatch`
is already a trigger. That deploy is a one-off publish to the public site, so
it is left to a human rather than run from an autonomous session.
