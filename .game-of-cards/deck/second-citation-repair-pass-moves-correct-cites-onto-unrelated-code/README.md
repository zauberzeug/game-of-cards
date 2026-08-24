---
title: second-citation-repair-pass-moves-correct-cites-onto-unrelated-code
summary: "refine-deck's citation-repair recipe anchored each cite at the card's CREATING commit, but once a repair pass has rewritten a cite's line number that commit no longer knows what the number means; replayed one week after this deck's first repair pass, that recipe would have moved 165 citations that were correct onto unrelated code. The anchor is now the commit that last WROTE the number, found by walking the card README's own history for the commit where the cite token turns from absent to present, which degenerates to the creating commit on a deck no pass has repaired. reference.md's claim that the creating-commit anchor made the check independent of earlier repair passes is replaced by the measurement that refutes it."
status: done
stage: null
contribution: high
created: "2026-08-17T02:21:41Z"
closed_at: "2026-08-17T04:39:57Z"
human_gate: none
advances:
  - re-run-safety-is-proven-per-verb-and-new-verbs-keep-missing-it
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the recipe the skill specifies agrees with the introduction-commit anchor on every open-card cite, including the ones a prior pass rewrote.
  - [x] TDD: a regression case covers the two-pass shape directly rather than only the live deck — a card whose cite was rewritten once, then whose target moved again, is repaired to the right line. It must fail on today's recipe.
  - [x] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` step 2 of the citation check no longer says "the card's creating commit". It names the commit that last WROTE the cited number, and gives the `git log --follow` walk that finds it.
  - [x] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" drops the claim that the creating-commit anchor makes the check independent of earlier repair passes, and states the real invariant: a cite means what it meant when its number was last authored.
  - [x] MECHANICAL: all five mirrors regenerate from the template — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are both clean.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# The second citation-repair pass moves correct cites onto unrelated code

> Later evidence: the last-write anchor this card installed is right for
> *repairing* a cite and wrong for *detecting* a stale card — the repair
> relocates the number and erases the signal. See
> [`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

## Location

- `goc/templates/skills/refine-deck/SKILL.md:115` — step 2 of the defunct-citation check, now the history walk.
- `goc/templates/skills/refine-deck/reference.md:129-151` — § "Citation anchor check", **Getting the anchor** + **Why not the creating commit**.
- `tests/test_refine_deck_citation_anchor.py` — the two-pass regression fixture.
- Mirrors carrying the same text: `.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`.

## What was broken

The skill shipped this rule for where to read a cite's anchor until
2026-08-17:

> 2. Anchor = that line's text at the card's creating commit
>    (`git log --diff-filter=A -- <card>/README.md`, last entry).

and `reference.md` justified that choice explicitly:

> Anchoring at the creating commit rather than at HEAD is what makes the
> check independent of any earlier repair pass.

The justification inverts the actual behaviour. The creating commit knows
what a cite meant **only while the number the card was filed with is still
the number in the file**. A repair pass rewrites that number — that is its
whole job. From then on the number was authored by the *repair* commit, and
reading it at the *creating* commit returns whatever unrelated code happened
to occupy that offset back when the card was filed.

The recipe then does the damage. It compares that unrelated text against
HEAD, finds them different, declares the cite defunct, and relocates the
cite to wherever the unrelated text lives now — passing the skill's own
safety guard, because the text it matched is genuinely unique and genuinely
non-trivial. The guard bounds *guessing*; it cannot detect that the recipe
anchored on the wrong line to begin with.

A worked instance from this deck. Card
[goc-help-omits-install-and-upgrade-subcommands](../goc-help-omits-install-and-upgrade-subcommands/)
was filed 2026-05-30 citing `goc/engine.py:2576-2748` for the `_build_parser`
subparser registrations. The 2026-08-10 pass correctly repaired that to
`3651-3855`, where `subparsers = parser.add_subparsers(dest="command")` then
lived. One week later:

| Recipe | Anchor read for line 3651 | Verdict |
|---|---|---|
| shipped (creating commit `0b810c30`) | `f"  push failed after rebase: …"` | relocate to 5226 — an unrelated push-retry branch |
| corrected (introduction commit `69e1e4f2`) | `subparsers = parser.add_subparsers(dest="command")` | relocate to 3819 — `_build_parser`, correct |

The corrected anchor is not a different *kind* of check. It is the same
content anchor, read at the commit that last wrote the number instead of the
commit that created the card. For a cite no pass has ever touched the two
commits are the same, so the recipes agree on a virgin deck and diverge only
on repaired ones — which is why the defect could not surface until a second
pass ran.

## Empirical evidence

`reproduce.py` reads the anchor rule out of the shipped skill body and
replays it over every open-card cite in this repo, scoring it against the
introduction-commit reference and carrying the retired rule as a standing
counterfactual. After the fix:

```
open-card cites replayed: 859
cites whose number a repair pass rewrote: 485

anchor named by goc/templates/skills/refine-deck/SKILL.md step 2: authoring-commit

Specified recipe vs reference anchor (the commit that INTRODUCED the cite):

  moves a cite that is CORRECT today : 0
  moves a cite to the WRONG line     : 0
  declines a cite it should repair   : 0
  agrees with the reference recipe   : 859

Counterfactual — the retired creating-commit anchor, same cites:

  moves a cite that is CORRECT today : 165
  moves a cite to the WRONG line     : 2
  declines a cite it should repair   : 3
  agrees with the reference recipe   : 689

PASS: the recipe the skill specifies agrees with the reference anchor
on every cite, including the ones an earlier pass rewrote.
```

The counterfactual row is the defect as it was measured when this card was
filed: 170 of 850 open-card cites wrong in one direction or another, 165 of
them correct cites that the pass would have moved onto unrelated code.
Measured earlier still, on the pre-repair tree (commit `67692824`, before
the 2026-08-17 pass corrected the numbers), the same replay put the shipped
recipe at 197 cites relocated to a wrong line, 44 correct cites moved, and
167 repairable cites declined — 408 of 851 wrong, against 343 agreements.

The live-deck replay can only ever measure a deck that has already been
repaired once, so `tests/test_refine_deck_citation_anchor.py` builds the
two-pass shape from scratch — file a cite, drift it, repair it, drift it
again — and asserts the recipe the skill prose specifies lands on the code
the card is about (line 16 of the fixture) rather than on the decoy the
creating-commit anchor finds (line 21). It fails on the retired recipe.

## Why it matters

The failure is silent and self-amplifying, and it degrades exactly the
artifact the pass exists to protect.

It is silent because a relocated cite still points at a real line of real
code. Nothing in `goc validate` reads citations, and the pass's own output
reports the rewrite as a repair. A reader who follows the cite lands on
plausible code in the right file and has no signal that the card no longer
describes it.

It is self-amplifying because each pass re-anchors on the previous pass's
output. Once a cite has been moved onto unrelated code, the next pass reads
*that* text as the anchor and tracks it faithfully forever. The card's real
subject is not recoverable from the cite after the first corruption; only
the card's prose still knows.

And it fires under normal conditions rather than rare ones. This deck's
citations do not survive a week: 385 of its cites carried numbers written by
the 2026-08-10 pass, and 260 of those had already drifted again by
2026-08-17, because `goc/engine.py` grew from 6730 to 6978 lines. Repair is
routine, so second passes are the normal case, not the edge case — see
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
for that measurement and what it argues for.

The blast radius is every consuming repo, not just this one. `refine-deck`
ships in all five plugin payloads, and the recipe is stated in the skill body
that an agent follows literally.

The 2026-08-17 hygiene pass on this repo deviated from the shipped recipe and
used the introduction-commit anchor instead; commit `f290f5f7` records that
deviation and its reasoning. The fix below promotes that deviation to the
rule, so the next pass to follow the skill as written preserves its work
instead of undoing it.

## Fix

"The card's creating commit" is gone from both files, replaced by the commit
that last WROTE the cite's number. Finding it is a walk over the README's own
history rather than a single `git log` call: list the README's commits oldest
to newest, read the file at each, and take the newest commit at which the
exact cite token transitions from absent to present. That commit is where the
number was authored — the filing commit for a virgin cite, the repair commit
for a repaired one — so the rule subsumes the old behaviour rather than
replacing it.

- `SKILL.md` step 2 carries the walk itself, because an agent that has to
  follow a pointer to learn the anchor will use the one-liner in front of it.
  The body cap in `tests/test_skill_body_size.py` rose 11,200 → 11,500 for it.
- `reference.md` § "Citation anchor check" states the invariant — a cite
  means what it meant when its number was last authored — and its new
  **Why not the creating commit** paragraph carries the measurement in place
  of the retired independence claim.
- Both surfaces are guarded: `tests/test_refine_deck_citation_anchor.py`
  parses the anchor rule out of each and requires them to name the same
  commit, then runs the parsed rule against the two-pass fixture.

`reproduce.py` in this directory holds the same walk (`intro` in `main()`)
and now reads its subject rule from `SKILL.md`, so it measures what the
shipped instructions do rather than a copy of them.
