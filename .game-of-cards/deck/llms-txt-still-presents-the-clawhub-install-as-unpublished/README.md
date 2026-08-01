---
title: llms-txt-still-presents-the-clawhub-install-as-unpublished
summary: "`site/llms.txt` — the file LLMs ingest to learn how to recommend GoC — still gates the OpenClaw install behind a publish that landed ten releases ago, telling readers the ClawHub channel only works \"Once the plugin is published\" and that until then they should build from source. ClawHub serves `game-of-cards` at the current release (latestVersion 0.0.27), and README.md, ABOUT.md, goc.md and site/index.html all present `openclaw skills install game-of-cards` as live — llms.txt is the single surface still saying otherwise. An LLM reading it steers OpenClaw users into a from-source build instead of the one-line registry install."
status: active
stage: null
contribution: high
created: "2026-08-01T05:34:31Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `site/llms.txt` no longer carries a pending-publish caveat, and its four sibling surfaces still agree the ClawHub install is live
  - [ ] TDD: a regression test asserts `site/llms.txt` presents every install channel it lists as available, so the next stale-caveat regression fails CI instead of shipping
  - [ ] MECHANICAL: the `## Install (OpenClaw)` section reads as a live registry install, and the reference to the internal card slug `publish-openclaw-plugin` is gone from the public document
  - [ ] MECHANICAL: `add-openclaw-install-section-to-llms-txt` (closed) carries a forward pointer to this card
  - [ ] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# llms.txt still presents the live ClawHub install as unpublished

## Location

`site/llms.txt:78` and `site/llms.txt:86` — the `## Install (OpenClaw)`
section:

````text
Once the plugin is published, install via ClawHub:

```sh
openclaw skills install game-of-cards
```

The same artifact is published to npm as `game-of-cards`; consumers that
prefer npm can add it via OpenClaw's plugin loading mechanism (see
<https://docs.openclaw.ai/plugins>).

Until publish lands (tracked under `publish-openclaw-plugin`), build from
source against this repo's plugin payload at
<https://github.com/zauberzeug/game-of-cards/tree/main/openclaw-plugin>.
````

`site/llms.txt` is the deployed `/llms.txt` — the workflow synthesizes a
second, staler copy, but the `site/` walk overwrites it (see
[pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order](../pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order/)).
So this text is what `game-of-cards.com/llms.txt` serves today.

## What's broken

Both sentences assert that the ClawHub channel is not installable yet. It is.
The package has been live on ClawHub since 2026-05-10 and tracks the current
release:

```console
$ curl -sS https://clawhub.ai/api/v1/packages/game-of-cards
name: game-of-cards
displayName: Game of Cards
latestVersion: 0.0.27
channel: community
family: bundle-plugin
createdAt (UTC): 2026-05-10T05:45:04.843000+00:00
updatedAt (UTC): 2026-07-14T04:19:08.769000+00:00
```

`0.0.27` is this repo's current release (`goc/__init__.py:7`, `git tag`
head `v0.0.27`) — ten patch releases after the publish landed. The npm leg is
live too (`registry.npmjs.org/game-of-cards` reports `latest: 0.0.27`, 21
versions), which llms.txt already describes correctly in the present tense one
paragraph above the stale sentence.

Every other surface in the repo says the channel is live and unconditional:

- `README.md:45` — "**OpenClaw plugin** — `openclaw skills install game-of-cards`."
- `ABOUT.md:82` — "Consumers install with `openclaw skills install game-of-cards`".
- `goc.md:225` — the same command in the OpenClaw install block.
- `site/index.html:153` — `<code>openclaw skills install game-of-cards</code> via
  OpenClaw / ClawHub`, in the same directory as the file that contradicts it.

AGENTS.md § "Common commands" states the contract those four reflect:
"Releases publish to three registries — PyPI, npm, ClawHub — all via OIDC
trusted publishing", and `.github/workflows/release.yml` carries the
`publish-clawhub` job plus the `redispatch-clawhub` job that fires it on the
tag ref. The blockers that once made the leg fail are all closed
(`clawhub-publish-fails-with-package-belongs-to-another-publisher`,
`clawhub-publish-fails-on-every-release-until-manual-tag-redispatch`,
`clawhub-package-publishes-pre-rewrite-package-json`).

## How it got stale

`add-openclaw-install-section-to-llms-txt` closed 2026-05-09 and authored this
section while the publish was genuinely pending, so the caveat was correct on
the day it was written. The ClawHub publish landed 2026-05-10 and the npm
publish shortly after; the three llms.txt cards that touched the file since
(`lead-llms-txt-with-claude-code-plugin`,
`llms-txt-still-recommends-uv-tool-install-as-preferred`, and the coverage card
`add-openclaw-coverage-to-readme-personas-and-website`) each edited a different
section and left the caveat standing.

The caveat points at `publish-openclaw-plugin` as its tracker. That card is
itself stale — `open`, `human_gate: session`, `0/8` DoD, with all seven of its
`advanced_by` prerequisites closed — so following the pointer does not correct
the reader either. Reconciling that card's state is deck hygiene for
`Skill(refine-deck)` and a human (its gate is `session`); it is deliberately
out of scope here, and this card's fix does not depend on it.

## Empirical evidence

`reproduce.py` compares the repo's own surfaces — offline and deterministic,
so the exit code does not depend on network access (output verbatim):

```
[FAIL] site/llms.txt gates a live install channel behind a pending publish
       site/llms.txt:78: Once the plugin is published, install via ClawHub:
       site/llms.txt:86: Until publish lands (tracked under `publish-openclaw-plugin`), build from source against this repo's plugin payload at <https://github.com/zauberzeug/game-of-cards/tree/main/openclaw-plugin>.
       contradicted by 4 surface(s) that print 'openclaw skills install game-of-cards' with no caveat:
         - README.md
         - ABOUT.md
         - goc.md
         - site/index.html
```

It exits 1 today and 0 once the section stops gating the channel.

## Why it matters

`llms.txt` exists for exactly one audience: a model deciding how to tell a user
to install this project. It is the document `site/index.html` and `goc.md` both
point crawlers at, and the one URL where a wrong install recipe propagates
without a human ever reading it. A model that ingests this section will tell an
OpenClaw user to clone the repo and build the plugin payload from source —
skipping a registry install that has worked for ten releases, on a runtime
whose whole selling point in the same file is that `python3` is the only host
prerequisite.

This is the same failure shape as
[pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order](../pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order/),
one layer up: that card is about two divergent *copies* of llms.txt, this one
is about the surviving copy diverging from the four surfaces it is supposed to
summarize. Neither is caught by anything today — no check ties llms.txt's
claims to the rest of the repo, which is why the regression test in the DoD
matters more than the one-time edit.

## Fix

In `site/llms.txt`, drop the publish-pending framing from the
`## Install (OpenClaw)` section:

- Line 78: `Once the plugin is published, install via ClawHub:` →
  `Install via ClawHub:`
- Line 86: replace the "Until publish lands (tracked under
  publish-openclaw-plugin), build from source…" sentence with a from-source
  pointer that carries no claim about publish state, and no reference to an
  internal card slug a public reader cannot resolve.

Then add a regression test alongside the other repo-local doc guards
(`tests/test_version_surfaces.py`, `tests/test_guidance_accuracy.py`) that
fails when `site/llms.txt` describes a listed install channel as pending. The
guard is repo-local — it checks this project's published website copy, not
anything goc ships to consumers — so it belongs in `tests/`, not in the engine.
