---
title: card-schema-reference-links-to-a-deck-card-no-consumer-repo-has
summary: "The shipped card-schema skill reference links the value-chain rule's provenance to a card in goc's OWN deck via a relative path. Nothing resolves it in a consuming repo: a fresh goc install writes a link to a card the consumer's deck has never contained, and in the source-of-truth template itself the path is one level short and resolves into a nonexistent goc/.game-of-cards. It survives review because the five mirrors sit three levels below this repo's root, so the link happens to resolve there."
status: done
stage: null
contribution: medium
created: "2026-07-29T06:28:25Z"
closed_at: "2026-07-29T06:33:48Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no shipped skill tree links into a `.game-of-cards/deck/` path, in the source-of-truth template or any mirror
  - [x] TDD: `tests/test_skill_template_deck_links.py` sweeps all six shipped skill trees and fails on any deck link, and proves it can catch the historical offending line rather than only reporting a clean tree
  - [x] MECHANICAL: `goc/templates/skills/card-schema/reference.md` cites the decision as a bare backticked title, matching the same file's citation of `rename-blocks-to-advances-and-design-value-sort`
  - [x] MECHANICAL: `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` both exit zero with the mirrors regenerated
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# The shipped card-schema reference links to a card only goc's own deck has

## Location

`goc/templates/skills/card-schema/reference.md:218-220`, closing the
"Value-chain rule" section:

```markdown
Decided in
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../../../.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
(Option E, 2026-05-26).
```

The same authored line reaches every reader through five mirrors:
`.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`,
`codex-plugin/skills/` (auto-synced by `scripts/sync_plugin_assets.py`)
and `openclaw-plugin/skills/` (hand-ported by
`scripts/port_skills_to_openclaw.py`).

## What's broken

`goc/templates/skills/card-schema/` is **package data** — `goc install`
copies it into a consuming repo's `.claude/skills/card-schema/`, and the
two plugin payloads ship it verbatim. The link target is a card in *this*
repo's deck. No consuming repo has ever contained it, so the citation is
dead the moment it ships.

It is dead in the source tree too, for a second and independent reason.
The template lives four directories below the repo root
(`goc/templates/skills/card-schema/`), so `../../../` reaches `goc/`, not
the root — the target resolves to `goc/.game-of-cards/deck/…`, which does
not exist. The path was written in the *installed* frame
(`.claude/skills/<name>/` is three deep), not the frame of the file that
holds it.

That mismatch is also why the line survived review. All five mirrors sit
exactly three directories below this repo's root, so in a `git clone` of
*this* repo the link resolves and looks healthy; only the
source-of-truth copy is visibly broken, and only from a path nobody
clicks. A reviewer checking the rendered mirror sees a working link to a
real card.

Eight lines further down, the same file cites another card in this repo's
deck — and does it the other way, with no link at all
(`reference.md:226`):

```markdown
(~80% loose value contribution, ~20%
strict prerequisite — see
`rename-blocks-to-advances-and-design-value-sort`) governs **start
ordering, not closure**.
```

A bare backticked title keeps the provenance a reader can search for
without promising a file that is not there. Line 219 is the outlier
against the file's own convention, and it is the only markdown link into
a `.game-of-cards/deck/` path anywhere in the shipped skill surface.

## Empirical evidence

`uv run python .game-of-cards/deck/card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/reproduce.py`
before the fix:

```
1. Source-of-truth template — does the relative target resolve?
   goc/templates/skills/card-schema/reference.md:219
     target   ../../../.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/
     resolves /home/runner/work/game-of-cards/game-of-cards/goc/.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose
     exists   False

2. Fresh `goc install --claude --local-skills` — what does a consumer get?
   consumer deck contents: ['.goc-version', 'log.md']
     link target  ../../../.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/
     resolves     /tmp/tmpukmsj210/consumer/.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose
     exists       False

3. Deck links across every shipped skill tree:
   goc/templates/skills/card-schema/reference.md:219  [BROKEN-here]
   .claude/skills/card-schema/reference.md:219  [resolves-here]
   .codex/skills/card-schema/reference.md:219  [resolves-here]
   claude-plugin/skills/card-schema/reference.md:219  [resolves-here]
   codex-plugin/skills/card-schema/reference.md:219  [resolves-here]
   openclaw-plugin/skills/card-schema/reference.md:219  [resolves-here]

FAIL: 6 shipped skill line(s) link into a `.game-of-cards/deck/` path. A
consuming repo has none of goc's own cards, so every one of these is dead
on install.
```

Step 2 is the consumer case end to end: a scratch `git init` repo, a real
`goc install --claude --local-skills`, and the installed skill's own link
resolved against the deck that install just scaffolded — which holds
`.goc-version` and `log.md` and nothing else.

After the fix, the same script reports:

```
3. Deck links across every shipped skill tree:
   none — the shipped skill bodies link to no deck path.

PASS: no shipped skill body links into a deck path.
```

`tests/test_skill_template_deck_links.py` was checked against a
reintroduced offender before closure: with the original line restored in
the template, `test_no_shipped_skill_body_links_into_a_deck` fails and
names `goc/templates/skills/card-schema/reference.md:219`; with the fix
in place all five tests pass. The guard is sensitive, not merely quiet.

## Why it matters

`card-schema/reference.md` § "Value-chain rule" is the passage an agent
reads when it has hit the `advanced-by-closed` closure gate and needs to
decide between waiting for the upstream card and retracting a false edge.
The link is the provenance for that ruling — the one pointer a reader who
distrusts the rule would follow. In a consuming repo it goes nowhere, so
the rule reads as asserted rather than decided, and the reader's next move
is to hunt a path that does not exist.

Reachability is total, not conditional: the line is package data. Every
`goc install --local-skills`, every Claude Code plugin install, every
Codex plugin install, and every OpenClaw plugin install writes it.

Same shape, different site, as
[next-card-reclassify-checklist-cites-nonexistent-docs-framework-path](../next-card-reclassify-checklist-cites-nonexistent-docs-framework-path/)
— a shipped skill body carrying a path that only goc's own repo could
satisfy. That one is prose naming a directory; this one is a resolvable
markdown link, which is why a guard can settle this class mechanically
where prose needs judgement. Filed as an instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/):
the deck-link axis is a tree-derived doc fact that nothing sweeps, so the
guard this card adds is a piece of that root's value.

## Fix (landed)

The link is gone; the citation stays, in the form `reference.md:226`
already used eight lines below —
`goc/templates/skills/card-schema/reference.md:218-220`:

```markdown
Decided in
`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`
(Option E, 2026-05-26).
```

`scripts/sync_plugin_assets.py` regenerated the four auto-synced mirrors
and `scripts/port_skills_to_openclaw.py` re-ported the OpenClaw copy;
both `--check` modes exit zero.

The guard is the durable half. `tests/test_skill_template_deck_links.py`
sweeps all six shipped skill trees for a markdown link whose target routes
through `.game-of-cards/deck/` and fails on any hit — a rule that holds in
any consuming repo, since none of them can have goc's cards, so there is
no false-positive surface to trade against. The predicate is anchored on
markdown link syntax, not the bare path, because several skills
legitimately print `.game-of-cards/deck/` in preflight probes and command
examples; naming the directory is fine, promising a file is not. URL
targets are out of scope for the same reason — they resolve for every
reader or none, independent of the install.

Per `static-source-guards-never-prove-they-can-catch-an-offender`, the
suite also feeds the historical offending line to the predicate and
asserts it fires, and pins that each swept tree really holds skill bodies,
so a guard that silently stopped matching fails rather than passing on a
clean tree.

Note that the four prose sites that name a deck path *without* linking it
(`kickoff`, `codex-kickoff`, `openclaw-kickoff`, `retrospective`) are
deliberately untouched: they instruct a reader to run a command against
their own deck, which is correct in every repo.
