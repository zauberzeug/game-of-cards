---
title: installed-files-point-readers-at-a-deck-folder-install-never-creates
summary: "Two shipped templates cite a *specific* goc card directory under the pre-move `deck/` root — the project-state README's closing bullet points at `deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md` (card renamed since, deck moved since), and `refine-deck/reference.md` points at `deck/auto-validate-card-titles-summaries-and-dods/log.md` (no card of that name ever existed). Both ship verbatim into every consuming repo, where goc's cards have never existed, so each is a dead pointer on arrival. The existing guard `tests/test_skill_template_deck_links.py` already sweeps the tree holding the second one and misses it purely on syntax: it matches markdown-link `](...)` targets, and both offenders are inline code."
status: done
stage: null
contribution: medium
created: "2026-09-20T04:39:00Z"
closed_at: "2026-09-20T04:46:36Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero (no shipped template cites a concrete goc card directory).
  - [x] TDD: the guard is fed both historical offending lines verbatim and asserted to fire, per `static-source-guards-never-prove-they-can-catch-an-offender`.
  - [x] TDD: precision is pinned — the `deck/<title>/` placeholder shorthand used at 19 sites per skill tree stays legal, and so does naming `.game-of-cards/deck/` bare.
  - [x] MECHANICAL: `goc/templates/game_of_cards/README.md` drops the extraction-era bullet; `goc/templates/skills/refine-deck/reference.md` drops the dead card pointer.
  - [x] MECHANICAL: the guard also sweeps the four `templates/game_of_cards` trees, so the project-state templates are covered at all.
  - [x] PROCESS: `python scripts/sync_plugin_assets.py --check` green, `python3 scripts/port_skills_to_openclaw.py --check` green, `uv run goc validate` clean, full `unittest` suite green.
---

# Installed files point readers at a deck folder install never creates

## Location

- `goc/templates/game_of_cards/README.md:89-91` — last bullet of `## Authoring guidelines`:

  ```
  - **Sub-card 6 handles migration.** When phasor-agents migrates off
    the vendored `deck.py`, this directory will be authored from the
    audit catalogue (`deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`).
  ```

- `goc/templates/skills/refine-deck/reference.md:391` — `## Quality-pass --llm flag`:

  ```
  Currently a stub; the integration story is
  tracked in `deck/auto-validate-card-titles-summaries-and-dods/log.md`.
  ```

- `tests/test_skill_template_deck_links.py` — the guard that should already
  own this rule, and its `SHIPPED_SKILL_TREES` / `DECK_LINK_RE` pair.

## What's broken

Both lines name a **concrete card directory**, not the `deck/<title>/`
placeholder the rest of the shipped docs use. A consuming repo has none of
goc's cards, so neither path can ever resolve there. Neither resolves in
goc's own repo either:

- `goc-package-pyproject-and-pypi-release` was renamed to
  `package-pyproject-and-pypi-release`, and the deck moved from `deck/` to
  `.game-of-cards/deck/`. The citation is stale on both axes at once; the
  file it means is at
  [`package-pyproject-and-pypi-release`](../package-pyproject-and-pypi-release/)`/audit_catalogue.md`.
- `auto-validate-card-titles-summaries-and-dods` matches no card under any
  name — the pointer has never resolved.

The README bullet is worse than a broken path: it is extraction-era residue.
It sits under `## Authoring guidelines`, three bullets that tell a consumer
how to author their own stubs, and instead describes a one-time migration of
the repo goc was extracted from. It has no generic reading — there is no
consuming-repo meaning for "when \<that repo\> migrates off the vendored
`deck.py`" — so there is nothing to generalize, only to remove.

`tests/test_skill_template_deck_links.py` already states exactly this rule in
its own docstring:

> A markdown link whose target routes through `.game-of-cards/deck/` therefore
> points at a card in *goc's own* deck — which no consuming repo has ever
> contained, so the link is dead the moment it ships.

and it already sweeps `goc/templates/skills`, the tree holding the second
offender. It misses both for two independent reasons:

1. `DECK_LINK_RE` anchors on markdown link syntax `](…)`. Both offenders are
   inline code spans, so the predicate never looks at them.
2. `SHIPPED_SKILL_TREES` lists only the six skill trees. The four
   `templates/game_of_cards` trees — which `goc install` copies into
   `.game-of-cards/` — are swept by nothing.

## Empirical evidence

`uv run python .game-of-cards/deck/installed-files-point-readers-at-a-deck-folder-install-never-creates/reproduce.py`,
as it printed at filing:

```
=== 1. concrete card directories cited by shipped templates ===
  goc/templates/game_of_cards/README.md:91: audit catalogue (`deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`).
  goc/templates/skills/refine-deck/reference.md:391: tracked in `deck/auto-validate-card-titles-summaries-and-dods/log.md`.

=== 2. do the cited cards resolve in goc's own repo? ===
  deck/goc-package-pyproject-and-pypi-release/                  exists: False
  .game-of-cards/deck/goc-package-pyproject-and-pypi-release/   exists: False
  .game-of-cards/deck/package-pyproject-and-pypi-release/       exists: True   <- renamed to this
  deck/auto-validate-card-titles-summaries-and-dods/            exists: False
  .game-of-cards/deck/auto-validate-card-titles-summaries-and-dods/exists: False

=== 3. does the README text reach a fresh `goc install`? ===
  <fresh repo>/.game-of-cards/README.md:91: audit catalogue (`deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`).
  <fresh repo>/deck/ created by install: False

[FAIL] 2 shipped template line(s) cite a goc card directory no installed repo has
```

Step 3 is the reachability proof: it runs a real `goc install` into a throwaway
git repo and finds the README line byte-identical in the installed copy, in a
repo where `deck/` was never created.

Step 4 pins why the standing guard let both lines through, and is the part that
stays meaningful after the fix — it feeds each historical line to both
predicates rather than re-reading the repaired files:

```
=== 4. does the standing guard cover both offenders? ===
  link-only rule flags audit catalogue (`deck/goc-package-pyproject-and-pyp  False
  widened rule flags   audit catalogue (`deck/goc-package-pyproject-and-pyp  True
  link-only rule flags tracked in `deck/auto-validate-card-titles-summaries  False
  widened rule flags   tracked in `deck/auto-validate-card-titles-summaries  True
  guard sweeps goc/templates/skills:        True
  guard sweeps goc/templates/game_of_cards: True

[OK] no shipped template cites a concrete goc card directory
```

## Why it matters

The reachability path is `goc install` itself: step 3 above runs a real
install into a throwaway git repo and finds the README line byte-identical in
`<fresh repo>/.game-of-cards/README.md`. Every repo that has ever run
`goc install` carries it, and `.game-of-cards/README.md` is *evolving*-owned —
`goc upgrade` never overwrites it — so existing installs keep the line until
someone reconciles by hand. Fixing the template is what stops new installs
inheriting it.

This is the twentieth instance recorded on
[`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
and the sharpest argument that card makes for itself: the guard for this exact
rule already exists, already sweeps the right tree, and still let an offender
through — because guards written from one instance inherit that instance's
syntax. The closest sibling,
[`card-schema-reference-links-to-a-deck-card-no-consumer-repo-has`](../card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/),
is the card that wrote the guard; this one widens it on both axes it was
narrow on.
[`next-card-reclassify-checklist-cites-nonexistent-docs-framework-path`](../next-card-reclassify-checklist-cites-nonexistent-docs-framework-path/)
is the same family (extraction-era residue in a shipped skill) but is
`decision`-gated because `docs/framework/*.md` has a credible generalized
rewrite. This card has none, which is why it files gate-free.

## Fix

Landed as described:

1. `goc/templates/game_of_cards/README.md` — the
   `**Sub-card 6 handles migration.**` bullet is gone. Nothing replaced it;
   the three surviving bullets are the generic authoring guidance the section
   promises. The dogfood consumer copy at `.game-of-cards/README.md` got the
   same edit by hand — it is *evolving*-owned, so no sync regenerates it.
2. `goc/templates/skills/refine-deck/reference.md` — the `tracked in ...`
   clause is gone. The card it pointed at does not exist, so the guard's
   prescribed fallback (cite by bare backticked title) had nothing to cite;
   the surrounding sentences already say the flag is a stub and that the
   regex-only mode is the load-bearing path.
3. `tests/test_skill_template_deck_links.py` — widened on both axes it was
   narrow on. `CARD_PATH_RE` / `card_paths()` match a `deck/` path naming a
   hyphenated slug and promising a file inside it, in any syntax; the sweep
   now covers `SWEPT_TREES` (six skill trees + four `templates/game_of_cards`
   trees) and every file, not only `*.md` — `config.yaml` is shipped prose
   too. `test_card_slugs_are_hyphenated` re-derives the predicate's
   discriminator from the live deck, so a hyphenless slug fails loudly rather
   than blinding the guard.
4. `scripts/sync_plugin_assets.py` and `scripts/port_skills_to_openclaw.py`
   refreshed the mirrors; both `--check` modes are green.

## Scope boundary

The `deck/<title>/` **placeholder** is deliberately out of scope. It appears
at 19 sites in every skill tree (`deck/<title>/README.md`,
`deck/<title>/reproduce.py`, `deck/<title>/log.md`, …) and in
`game_of_cards/config.yaml`, always with the literal `<title>` stand-in. That
is a house shorthand used consistently, not a dead pointer — and whether it
should be respelled `.game-of-cards/deck/<title>/` everywhere is a separate
convention call over ~20 sites, filed as
[`shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates`](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/).
The guard added here must therefore keep the placeholder form passing, which
is what pins the two apart.
