---
title: citation-re-run-still-proposes-false-repairs-when-a-cite-inherits-its-siblings-old-number
summary: "FIXED 2026-11-20: when one commit moved a cite onto the number a sibling cite in the same card just vacated, the token never turned from absent to present, so the citation walk anchored the cite on the sibling's line and proposed moving a correct cite onto the sibling's code — twice in the 2026-11-16 pass's committed re-run. Step 2 of the refine-deck recipe now compares the cite's slot (its line with cite numbers masked, plus its place on that line) wherever the token is on both sides of a commit, and takes a commit that handed the token over as the one that wrote it; a slot reworded beyond its numbers reads as kept. Pinned by a same-commit hand-off fixture on two lines and inside one line."
status: done
stage: null
contribution: medium
created: "2026-11-16T02:11:21Z"
closed_at: "2026-11-20T04:43:54Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the closing re-run, replayed with the amended step 2 over its fixture, proposes no move. Its `replay()` must be updated to the amended rule; until then it exits 2 rather than judge a recipe it no longer matches.
  - [x] TDD: `tests/test_refine_deck_citation_anchor.py` gains a same-commit hand-off fixture that fails on today's recipe: two cites one shift apart in one card, both rewritten in one commit, and the recipe the skill prose specifies must not propose moving the cite that inherited its sibling's number.
  - [x] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` step 2 and `reference.md` § Citation anchor check say how a commit that keeps a token but changes which cite holds it is anchored or declined, and the reference no longer claims that committing alone makes the closing re-run valid.
  - [x] MECHANICAL: the two live instances are read against their prose at closure, and restored if any pass moved them: the summary's `_remove_from_list_field` cite on `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`, and the comment label beside `if check.returncode == 1:` on `claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset`.
  - [x] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: "claude[bot]", where: main}
---

# The citation re-run still proposes false repairs when a cite inherits its sibling's old number

## Location

- `goc/templates/skills/refine-deck/SKILL.md:162-177` — step 2 of the
  citation recipe. The walk takes the newest commit where the cite token
  turns from absent to present, and now also compares the cite's SLOT
  wherever the token is on both sides of a commit.
- `goc/templates/skills/refine-deck/reference.md:435-448` — **Getting the
  anchor**, which points forward to the slot comparison.
- `goc/templates/skills/refine-deck/reference.md:483-519` — **A commit can
  hand the token from one cite to another**: the shape, the slot, the
  reworded-line case, and the measurements below.
- `goc/templates/skills/refine-deck/reference.md:677` — the `retired
  occurrence` residue row, which now names the hand-off.
- `goc/templates/skills/refine-deck/reference.md:701-727` — **The commit
  comes first because the walk reads history**, which now calls the commit
  necessary, not sufficient.
- `tests/test_refine_deck_citation_anchor.py` — `documented_handoff_rule`,
  `cite_slots`, `handed_off`, `build_handoff_repo`, and the classes
  `DocumentedHandoffRuleTest`, `SameCommitHandoffTest` and
  `RewordedLineScopeTest`.
- `tests/test_skill_body_size.py` — the refine-deck cap, raised a twelfth
  time from 16,000 to 16,300 bytes.
- The five mirrors of both skill files (`.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).

## What was broken

The recipe identified a cite by its token. Step 2 said:

> Anchor = that line's text at the commit that last WROTE the number:
> walk `git log --follow --format=%H -- <card>/README.md` oldest →
> newest and take the newest commit where the cite token turns from
> absent to present — the filing commit for a virgin cite, the repair
> commit for one an earlier pass rewrote.

and the reference said when the closing re-run could be trusted:

> So the re-run is only valid once the rewrites are committed, which a
> local commit satisfies; pushing can wait for the verdict.

Committing makes a freshly written token turn from absent to present at
the pass's commit, unless the token was already present one version
earlier, held by a different cite of the same card. A uniform shift
produces exactly that whenever two cites of one card sit one shift
apart: the pass moves cite B off number N+k and cite A onto N+k in the
same commit. The token is present before that commit (B's) and after it
(A's), so it never turns there. The walk took the older turn, the commit
that wrote B's number, read B's line at that commit and found it
substantial and unique in HEAD. It proposed moving A onto B's code.
Every per-cite guard passed: the card holds the token once, the anchor
is not trivial, and the match is unique.

The `retired occurrence` row and its "commit, and re-run" remedy assumed
the colliding occurrence lay in an earlier commit than the pass's own. In
this shape the pass's own commit is what retires it, so committing
changed nothing the walk could see.

## Empirical evidence

`reproduce.py` reads which walk `SKILL.md` step 2 words and replays it over
the committed history of two throwaway repositories: a card citing two
functions 18 lines apart, once on two lines and once side by side on one
line, 18 lines of code inserted above both, and one repair commit that
moves both cites. Against step 2 as shipped (the bare token walk) it exits
1:

```
SKILL.md step 2 words the bare token walk; replaying it over committed history.

Cites on two lines. After the committed pass:
  src.py:28 = 'def alpha_function_for_the_fixture():'
  src.py:46 = 'def beta_function_for_the_fixture():'
Both cites name the function their prose names. Closing re-run:
  src.py:28  anchored at 'file the card': 'def beta_function_for_the_fixture():'
             HEAD line 28 is 'def alpha_function_for_the_fixture():'  -> PROPOSES src.py:46
  src.py:46  anchored at 'repair pass: re-anchor both cites': 'def beta_function_for_the_fixture():'  -> current
...
DEFECT: the re-run proposes 2 move(s) of a correct cite: ['src.py:28 -> src.py:46', 'src.py:28 -> src.py:46']
```

Against the amended step 2 (the slot-comparing walk) it exits 0: both
cites in both repositories anchor at the repair commit and read `current`.

On this deck, the 2026-11-16 pass committed 171 repairs (`4ca21b40`, all a
uniform +18 in `goc/engine.py`) and its closing re-run proposed two more,
both this shape and both false. Neither was applied:

```
bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
  engine.py:7139 -> engine.py:7157        anchored at 3ebd9b7e
claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset
  goc/engine.py:6010 -> goc/engine.py:6028   anchored at 3ebd9b7e
```

In the first card, the pass moved the summary's `_remove_from_list_field`
cite from 7121 to 7139 and the body's `_mutate_pair` cite from 7139 to
7157 in one commit; the old walk anchored the summary cite on
`_mutate_pair`. In the second, the label beside `if check.returncode ==
1:` went from 5992 to 6010 while the `claim_push_enabled` cite went from
6010 to 6028; the old walk anchored the label on `claim_push_enabled`.

Replayed over this deck's open and active cards on 2026-11-20 (568 cites
whose token occurs once in their card; 83 more are declined as repeated
tokens):

- **Hand-offs:** exactly the two above move an anchor; both trip both of
  the rule's tests (the new holder's slot held another number before, and
  the old holder's slot holds another number after).
- **Reworded lines:** one cite crossed a commit where its slot changed
  beyond its numbers on both sides — `f2b66fb3` rewording the sentence
  around `sync_plugin_assets.py:38-43` — and it was a prose edit that kept
  its number. Declining that shape would have been a false decline in the
  one case measured; anchoring on it would have read the reword's tree.
- **Same-line cites:** 65 of the 754 cites on those cards share their line
  with a cite of the same file, so a hand-off inside one line is
  reachable, and a slot without the cite's place on its line would miss
  it.
- **Both live instances, against HEAD** (the engine had grown 269 more lines
  since 2026-11-16, so neither cite resolved at HEAD any longer):

  | cite | bare token walk | slot walk |
  |---|---|---|
  | `engine.py:7139`, summary of the bare-string card | anchored at `3ebd9b7e` on `def _mutate_pair` → proposes 7426, the sibling's code | anchored at `4ca21b40` on `def _remove_from_list_field` → proposes 7408, correct |
  | `goc/engine.py:6010`, label in the claim-push card | anchored at `3ebd9b7e` on `def claim_push_enabled` → proposes 6295, the sibling's code | anchored at `4ca21b40` on `if check.returncode == 1:` → proposes 6277, correct |

  So the next pass would have applied both false moves in its FIRST round,
  where the "already resolves at HEAD" advice no longer reached them.

## Why it mattered

- A false proposal in a pass's first round is indistinguishable from a real
  repair. Applied, each lands a cite on a number its card already holds for
  the sibling, so from then on both occurrences decline as `ambiguous
  occurrence` and the damage is never reported again.
- The shape recurs whenever a file grows by one amount between passes and a
  card holds two cites exactly that far apart, which is common on cards
  citing a dozen `goc/engine.py` lines: 2 of 171 repairs on 2026-11-16.
- Related: [citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/)
  installed the commit-first rule this shape slipped past, and
  [citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide](../citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide/)
  the occurrence guard it passed. The citation-scheme decision on
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
  carries the cost record of recipe patches like this one.

## Fix (applied)

The walk follows the occurrence across a commit that keeps the token.
Where the token is present on both sides of a commit, step 2 compares its
SLOT before and after: the cite's line with every cite number masked, plus
its place among that line's cites. The same slot on both sides is one cite
keeping its number. A different slot is a hand-off, and that commit wrote
this cite's number, when the slot holding the token held another number
before, or the slot that held it holds another number after; the walk
anchors there as at a turn. A slot that changed beyond its numbers on both
sides is a reworded line, and the token was kept.

Two alternatives the filing named were not taken:

- **Declining where the walk cannot tell a hand-off from a prose edit.** The
  one measured case was a prose edit, so the decline would have been noise;
  a hand-off that also rewords both lines needs a commit that renumbers and
  rewrites prose at once, which a repair pass never does. The closing
  re-run still catches one, as a non-empty second round.
- **Promoting "already resolves at HEAD" to a numbered step.** It caught
  both live instances only while the file stood still. Four days later the
  engine had grown and neither cite resolved at HEAD, so the check no
  longer reached them, and it costs a prose read per cite. The reference
  keeps it as advice.

`SKILL.md` carries the rule in one sentence. Its cap in
`tests/test_skill_body_size.py` went from 16,000 to 16,300 bytes, the
twelfth raise, and the comment beside it records why a pointer alone would
fail: every per-cite rule passes on the move. The shape, the reworded-line
case and the measurements are in `reference.md`.
