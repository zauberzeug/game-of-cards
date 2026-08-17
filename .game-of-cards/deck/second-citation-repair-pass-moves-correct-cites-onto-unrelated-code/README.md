---
title: second-citation-repair-pass-moves-correct-cites-onto-unrelated-code
summary: "refine-deck's citation-repair recipe anchors each cite at the card's CREATING commit, but once a repair pass has rewritten a cite's line number that commit no longer knows what the number means. Replayed against this deck one week after its first repair pass, the shipped recipe would move 165 citations that are correct today onto unrelated code. reference.md claims the creating-commit anchor is what makes the check independent of any earlier repair pass; it is precisely what breaks it."
status: open
stage: null
contribution: high
created: "2026-08-17T02:21:41Z"
closed_at: null
human_gate: none
advances:
  - re-run-safety-is-proven-per-verb-and-new-verbs-keep-missing-it
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the recipe the skill specifies agrees with the introduction-commit anchor on every open-card cite, including the ones a prior pass rewrote.
  - [ ] TDD: a regression case covers the two-pass shape directly rather than only the live deck — a card whose cite was rewritten once, then whose target moved again, is repaired to the right line. It must fail on today's recipe.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` step 2 of the citation check no longer says "the card's creating commit". It names the commit that last WROTE the cited number, and gives the `git log --follow` walk that finds it.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" drops the claim that the creating-commit anchor makes the check independent of earlier repair passes, and states the real invariant: a cite means what it meant when its number was last authored.
  - [ ] MECHANICAL: all five mirrors regenerate from the template — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are both clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# The second citation-repair pass moves correct cites onto unrelated code

## Location

- `goc/templates/skills/refine-deck/SKILL.md:115` — step 2 of the defunct-citation check.
- `goc/templates/skills/refine-deck/reference.md:129-135` — § "Citation anchor check", **Getting the anchor**.
- Mirrors carrying the same text: `.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`.

## What's broken

The skill tells the pass where to read a cite's anchor:

> 2. Anchor = that line's text at the card's creating commit
>    (`git log --diff-filter=A -- <card>/README.md`, last entry).

and `reference.md` justifies that choice explicitly:

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

`reproduce.py` replays both anchors over every open-card cite in this repo,
one week after the first repair pass:

```
open-card cites replayed: 850

Shipped recipe (anchor at the card's CREATING commit) vs
corrected recipe (anchor at the commit that INTRODUCED the cite):

  moves a cite that is CORRECT today : 165
  moves a cite to the WRONG line     : 2
  declines a cite it should repair   : 3
  agrees with the corrected recipe   : 680

  sample — correct cites the shipped recipe would move:
    engine.py:1792 in support-custom-frontmatter-fields-with-enum-and-required-when-rules
      -> would be rewritten to line 4509
    install.py:1686 in plugin-context-detection-never-fires-on-real-marketplace-installs
      -> would be rewritten to line 1795
    goc/install.py:51 in install-auto-detects-codex-from-the-shared-agents-md-briefing-file
      -> would be rewritten to line 53

DEFECT PRESENT: the shipped recipe disagrees with the corrected anchor on 170 of 850 cites.
Running the documented pass a second time rewrites correct citations onto unrelated code.
```

Measured on the pre-repair tree (commit `67692824`, before the 2026-08-17
pass corrected them), the same replay put the shipped recipe at 197 cites
relocated to a wrong line, 44 correct cites moved, and 167 repairable cites
declined — 408 of 851 wrong in one direction or another, against 343 where
the two recipes agreed.

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
deviation and its reasoning. Without the fix below, the next pass to follow
the skill as written will undo that work.

## Fix

Replace "the card's creating commit" with "the commit that last wrote this
cite's number" in both files. Finding it is a walk over the README's own
history rather than a single `git log` call: list the README's commits oldest
to newest, read the file at each, and take the newest commit at which the
exact cite token transitions from absent to present. That commit is where the
number was authored — the creating commit for a virgin cite, the repair
commit for a repaired one — so the rule subsumes today's behaviour rather
than replacing it.

`reproduce.py` in this directory contains a working implementation of the
walk (`intro` in `main()`); it is the reference for the skill text.

The gate is `none` because the fix is determined: the recipe is wrong for a
stated reason, the corrected rule is a strict generalization of it, and the
implementation already exists and is measured. A reader who disagrees that
the skill should carry the full history walk — rather than, say, forbidding
repair passes from rewriting numbers at all — should raise the gate and say
so, but nothing about the defect itself is open.
