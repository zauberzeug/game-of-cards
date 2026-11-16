---
title: citation-re-run-still-proposes-false-repairs-when-a-cite-inherits-its-siblings-old-number
summary: "The citation pass ends with a re-run that must propose zero further repairs, and the recipe says the re-run is valid once the rewrites are committed. That fails when one commit moves a cite onto the line number a sibling cite in the same card just vacated: the token never turns from absent to present, so the walk anchors the cite on the sibling's old line and proposes moving a correct cite onto the sibling's code. The 2026-11-16 pass hit it twice after committing, and the next pass will propose the same two moves as ordinary repairs."
status: open
stage: null
contribution: medium
created: "2026-11-16T02:11:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the closing re-run, replayed with the amended step 2 over its fixture, proposes no move. Its `replay()` must be updated to the amended rule; until then it exits 2 rather than judge a recipe it no longer matches.
  - [ ] TDD: `tests/test_refine_deck_citation_anchor.py` gains a same-commit hand-off fixture that fails on today's recipe: two cites one shift apart in one card, both rewritten in one commit, and the recipe the skill prose specifies must not propose moving the cite that inherited its sibling's number.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` step 2 and `reference.md` § Citation anchor check say how a commit that keeps a token but changes which cite holds it is anchored or declined, and the reference no longer claims that committing alone makes the closing re-run valid.
  - [ ] MECHANICAL: the two live instances are read against their prose at closure, and restored if any pass moved them: the summary's `_remove_from_list_field` cite on `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`, and the comment label beside `if check.returncode == 1:` on `claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset`.
  - [ ] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
---

# The citation re-run still proposes false repairs when a cite inherits its sibling's old number

## Location

- `goc/templates/skills/refine-deck/SKILL.md:162-173` — step 2 of the
  citation recipe: the anchor is the newest commit where the cite TOKEN
  turns from absent to present.
- `goc/templates/skills/refine-deck/SKILL.md:203-210` — the closing
  re-run that must propose zero further repairs.
- `goc/templates/skills/refine-deck/reference.md:662-685` — **The commit
  comes first because the walk reads history**, which ends in the claim
  that committing makes the re-run valid.
- `goc/templates/skills/refine-deck/reference.md:638` — the `retired
  occurrence (re-run before the commit)` residue row and its remedy.
- `tests/test_refine_deck_citation_anchor.py:2249` —
  `RetiredOccurrenceRerunTest`, which builds only the earlier-pass shape.
- The five mirrors of both skill files (`.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).

## What's broken

The recipe identifies a cite by its token. Step 2 says:

> Anchor = that line's text at the commit that last WROTE the number:
> walk `git log --follow --format=%H -- <card>/README.md` oldest →
> newest and take the newest commit where the cite token turns from
> absent to present — the filing commit for a virgin cite, the repair
> commit for one an earlier pass rewrote.

and the reference says when the closing re-run can be trusted:

> So the re-run is only valid once the rewrites are committed, which a
> local commit satisfies; pushing can wait for the verdict.

Committing makes a freshly written token turn from absent to present at
the pass's commit, unless the token was already present one version
earlier, held by a different cite of the same card. A uniform shift
produces exactly that whenever two cites of one card sit one shift
apart: the pass moves cite B off number N+k and cite A onto N+k in the
same commit. The token is present before that commit (B's) and after it
(A's), so it never turns there. The walk takes the older turn, the
commit that wrote B's number, reads B's line at that commit and finds it
substantial and unique in HEAD. It proposes moving A onto B's code.
Every per-cite guard passes: the card holds the token once, the anchor
is not trivial, and the match is unique.

The `retired occurrence` row and its "commit, and re-run" remedy assume
the colliding occurrence lies in an earlier commit than the pass's own.
In this shape the pass's own commit is what retires it, so committing
changes nothing the walk can see.

## Empirical evidence

`reproduce.py` builds the shape in a throwaway repository: a card citing
two functions 18 lines apart, 18 lines of code inserted above both, and
one repair commit that moves both cites. It then replays step 2 as
`SKILL.md` words it over the committed history:

```
After the committed pass: src.py:28 = 'def alpha_function_for_the_fixture():'
                          src.py:46 = 'def beta_function_for_the_fixture():'
Both cites name the function their prose names.

Closing re-run, step 2 as SKILL.md words it, over committed history:
  src.py:28  anchored at 'file the card': 'def beta_function_for_the_fixture():'
             HEAD line 28 is 'def alpha_function_for_the_fixture():'  -> PROPOSES src.py:46
  src.py:46  anchored at 'repair pass: re-anchor both cites': 'def beta_function_for_the_fixture():'  -> current

DEFECT: the re-run proposes 1 move(s) of a correct cite: ['src.py:28 -> src.py:46']
The alpha cite would land on beta's definition, a number the card
already holds for beta. Committing first did not help: the token
src.py:28 never turned from absent to present.
```

On this deck, the 2026-11-16 pass committed 171 repairs (`4ca21b40`,
all a uniform +18 in `goc/engine.py`) and its closing re-run proposed
two more, both this shape and both false:

```
bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
  engine.py:7139 -> engine.py:7157        anchored at 3ebd9b7e
claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset
  goc/engine.py:6010 -> goc/engine.py:6028   anchored at 3ebd9b7e
```

In the first card, the pass moved the summary's `_remove_from_list_field`
cite from 7121 to 7139 and the body's `_mutate_pair` cite from 7139 to
7157 in one commit; the re-run anchors the summary cite on `_mutate_pair`.
In the second, the label beside `if check.returncode == 1:` went from
5992 to 6010 while the `claim_push_enabled` cite went from 6010 to 6028;
the re-run anchors the label on `claim_push_enabled`. Neither proposal
was applied, and both cites name their prose's code at HEAD.

## Why it matters

- The next pass makes both proposals in its FIRST round, where nothing
  sets them apart from real repairs. Applied, each lands a cite on a
  number its card already holds for the sibling, so from then on both
  occurrences decline as `ambiguous occurrence` and the damage is never
  reported again.
- The only thing that stops it today is the reference's advice that a
  cite which already resolves at HEAD is not a repair candidate
  ("Cheap, and worth running first"). That is advice in
  `reference.md`, not a numbered step, and it needs a prose read per
  cite.
- The shape recurs whenever a file grows by one amount between passes
  and a card holds two cites exactly that far apart, which is common on
  cards citing a dozen `goc/engine.py` lines: 2 of 171 repairs on
  2026-11-16.
- Related: [citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/)
  installed the commit-first rule this shape slips past, and
  [citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide](../citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide/)
  the occurrence guard it passes. The citation-scheme decision on
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
  carries the cost record of recipe patches like this one.

## Fix

Follow the occurrence, not only the token, across a commit that keeps
the token. When the token is present on both sides of a commit, compare
the lines that hold it with their digits masked: if the line holding it
after the commit is a different masked line from the one holding it
before, and that earlier masked line still exists after the commit
under another number, the commit handed the number from one cite to
another, and it is the commit that wrote this cite's number. Where the
walk cannot tell a hand-off from a prose edit, DECLINE (for example as
`ambiguous occurrence (hand-off)`) instead of taking the older turn. A
cheaper safety net that catches both live instances is to promote the
"already resolves at HEAD" check from reference advice to a numbered
step before relocation.

`SKILL.md` sits under the size cap in `tests/test_skill_body_size.py`,
so the rule goes there tersely and its reasoning and this measurement
go in `reference.md`. The `retired occurrence` row should name the
hand-off shape, or a new row should.
