---
title: ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card
summary: "The `ci.yml` header comment states \"All 11 skill templates ship as importable package data\" (there are 18) and says the deck-validation step becomes load-bearing \"Once `goc-install-command-scaffolds-repo` (sub-card 2) ships\" — a card title that has never existed (the real card, `install-command-scaffolds-repo`, closed long ago). Both claims mislead a reader auditing what CI actually covers."
status: open
stage: null
contribution: low
created: "2026-07-26T08:09:35Z"
closed_at: null
human_gate: session
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: the `ci.yml` header no longer hard-codes a skill count — it either states the invariant without a number, or the number matches `ls -1d goc/templates/skills/*/ | wc -l` at the time of the edit.
  - [ ] MECHANICAL: the stale forward-looking sentence is rewritten to describe what the step does today, and any card it cites resolves to a real deck directory.
  - [ ] PROCESS: decide whether a hard-coded count belongs in a comment at all, or whether the "Verify package data ships templates" step (which already derives the list from the filesystem) makes the number redundant.
---

# The CI header comment miscounts skill templates and cites a card that never existed

Two stale claims in the same eleven-line comment block, both about what CI
covers — the first thing a reader checks when auditing the build.

**Generalization:** this is instance seven of a catalogued shape — a prose claim
restating a fact the tree already knows, with no guard, found only after it had
already rotted. The architectural card is
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
(`human_gate: decision`). Both claims below land squarely in shapes that card
enumerates: a **bare count in prose** ("All 11 skill templates") and a
**forward-looking promise** with no expiry and no owner, naming a string that
appears nowhere in the tree. No `advances` edge — that card closes on its own
deliverable, so it is a governing cluster, not an aggregation epic.

This instance also widens the root card's surface list: its Option A sweep names
`AGENTS.md`, `goc.md`, `README.md`, `ABOUT.md`, `CONTRIBUTING.md`,
`DECK_LOCATION.md`, `PERSONAS.md`, `site/`, the plugin READMEs and the skill
bodies — **workflow-file comments are not on it**, and that is where these two
claims live.

## Location

`.github/workflows/ci.yml:1-11`

## What's broken

```yaml
# CI workflow — smoke-tests the package on every push and pull-request.
#
# Confirms:
#   - Package builds cleanly with hatchling
#   - `goc --version` reports correctly via the console-script entry point
#   - `goc validate` passes on the repo's own deck (once a deck exists)
#   - All 11 skill templates ship as importable package data
#
# Once `goc-install-command-scaffolds-repo` (sub-card 2) ships and the
# repo's own `deck/` directory contains cards, the `goc validate` step
# becomes the gate that keeps card frontmatter consistent.
```

**Claim 1 — "All 11 skill templates".** There are 18:

```
$ ls -1d goc/templates/skills/*/ | wc -l
18
```

The number was correct once and was never bumped as skills were added
(`claude-kickoff`, `codex-kickoff`, `openclaw-kickoff`, `decide-card`,
`retrospective`, `standup`, `upgrade`, …). The step it describes already
derives the list from the filesystem — `ci.yml:64` iterates
`goc/templates/skills` — so only the comment carries a number, and only the
comment can be wrong.

**Claim 2 — the card citation.** `goc-install-command-scaffolds-repo` does not
resolve:

```
$ ls -d .game-of-cards/deck/goc-install-command-scaffolds-repo
ls: cannot access '.game-of-cards/deck/goc-install-command-scaffolds-repo': No such file or directory
```

The real card is [`install-command-scaffolds-repo`](../install-command-scaffolds-repo/)
— `status: done`, `8/8`. So the sentence is doubly stale: it names a title that
never existed, and it frames a shipped capability as pending ("Once … ships").

## Why it matters

This is the header a reader consults to learn what the build actually
guarantees. The count invites the false inference that a missing skill would
show up as a shortfall against 11; the forward-looking sentence invites the
inference that deck validation is not yet load-bearing. The second inference is
wrong for a *different* reason too — see
[`ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory`](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/),
where the `if [ -d deck ]` guard means the validate step is currently a silent
no-op. The two cards touch the same file and should probably land together.

## Fix

Rewrite `ci.yml:1-11`. Drop the hard-coded count in favour of the invariant
("every skill template under `goc/templates/skills/` ships as importable
package data" — which is what the step checks), and replace the
"Once … ships" paragraph with a present-tense description of the validate step.

**Gate is `session`, not `none`, because the file is under
`.github/workflows/`** — the autonomous bot's `GITHUB_TOKEN` cannot write there
(the same constraint recorded in `AGENTS.md`, which is why the OpenClaw porter
drift guard lives in a test rather than a `ci.yml` step). A `pull-card` session
that claimed this at gate `none` would do the work and then fail to commit it.
