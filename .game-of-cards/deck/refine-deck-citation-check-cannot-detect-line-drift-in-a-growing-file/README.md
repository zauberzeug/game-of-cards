---
title: refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file
summary: "The refine-deck skill specified its defunct-citation check as `the cited file exists and the cited line is <= EOF`, a predicate that can only fire when a file SHRINKS past the cite. Source files grow, so a citation whose target moved thousands of lines away still passed. Replaying every citation this deck's open cards carried at filing time, 728 of 806 now point at unrelated code and the bounds test flagged 0 of them, so every consuming repo's hygiene pass reported a clean deck while the citations rotted. Replaced by an anchor test plus a repair recipe that declines rather than guesses: recall 728/728, zero false positives."
status: done
stage: null
contribution: high
created: "2026-08-10T02:38:28Z"
closed_at: "2026-08-10T05:02:51Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — every citation whose line content changed
        since filing is reported by whatever check the skill specifies.
  - [x] MECHANICAL: the `### Defunct file:line citations` section of
        `goc/templates/skills/refine-deck/SKILL.md` no longer specifies `<= EOF` as
        the test. It specifies an anchor-based check that compares what is AT the
        cited line against what the card says is there, and states plainly that an
        in-range line number is not evidence the citation is current.
  - [x] MECHANICAL: the section gives the repair recipe, not just the detection —
        resolve each cite against the cited file at the card's creating commit,
        relocate that line's text in HEAD, and rewrite the number only when the
        match is unique and non-trivial. Bare-basename cites (`engine.py:N` for
        `goc/engine.py:N`) resolve too.
  - [x] MECHANICAL: all five mirrors regenerate from the template and
        `python scripts/sync_plugin_assets.py --check` plus
        `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [x] PROCESS: the residue is stated rather than hidden — the recipe cannot map a
        cite whose line text was deleted or is ambiguous, so the section says those
        are reported for a human read instead of silently skipped.
---

# The defunct-citation check cannot detect line drift in a file that grows

## Location

- `goc/templates/skills/refine-deck/SKILL.md:103` — the specification, now the
  anchor test; `reference.md:111` § "Citation anchor check" carries its long form.
- The same section ships in all five mirrors: `.claude/skills/refine-deck/SKILL.md`,
  `.codex/skills/refine-deck/SKILL.md`, `claude-plugin/skills/refine-deck/SKILL.md`,
  `codex-plugin/skills/refine-deck/SKILL.md`,
  `openclaw-plugin/skills/refine-deck/SKILL.md`.

## What was broken

The skill defined the check as, verbatim until this card closed:

> For each open card, check its body cites against current code:
> verify each cited file exists and the cited line is ≤ EOF. A defunct
> citation usually means the cited code was refactored.

The second clause is the defect. `line <= EOF` is a *bounds* test, but citation rot
is a *displacement* problem, and the two only coincide when a file shrinks past the
cited line. Files grow. `goc/engine.py` was 4501 lines at the commit that filed the
oldest card in this sample and is 6730 lines today; `goc/install.py` is 1837. Every
citation that was valid when written is therefore still ≤ EOF, no matter how far the
code it named has moved. The predicate's true positives are confined to the rare
case of a file that shrank, and its silence is indistinguishable from a clean deck.

The skill's own prose shows it means to catch displacement — it says a defunct
citation "usually means the cited code was refactored", and prescribes updating the
number in place. A refactor that moves code *down* is the common case and the one
the specified test cannot see.

## Empirical evidence

`reproduce.py` replays each open card's citations as they stood in the README blob
at that card's creating commit, so the measurement is independent of any later
repair. Ground truth per cite is read straight off the two blobs — the cited line no
longer holds the text it held at filing — and both predicates are scored against it:
the `≤ EOF` bounds test the section used to specify, and the anchor test it specifies
now.

```
open cards examined            : 182
citations replayed at filing   : 806

  unchanged since filing       : 78
  DRIFTED (ground truth)       : 728

verdicts on the drifted set:
  bounds test `line <= EOF`    : 0 reported, 728 missed
  anchor test (current spec)   : 728 reported, 0 missed
      auto-repairable          : 521
      residue, human-reported  : 207  (ambiguous 87, anchor absent 28, trivial 92)

  anchor test on the 78 unchanged cites: 0 false positives

  examples from the drifted set:
    active-state-conflates-being-worked-on-with-parked-at-human-gate
      cite goc/engine.py:2443 in a 6730-line file, so the bounds test says CLEAN
      at filing: 'def render_leverage_line('
      today    : 'The single "not yet real" predicate consulted by the termina'  -> L3424
    active-state-conflates-being-worked-on-with-parked-at-human-gate
      cite goc/engine.py:2477 in a 6730-line file, so the bounds test says CLEAN
      at filing: ')'
      today    : 'return False'  -> residue: trivial
    active-state-conflates-being-worked-on-with-parked-at-human-gate
      cite goc/engine.py:2480 in a 6730-line file, so the bounds test says CLEAN
      at filing: 'def render_active_notice('
      today    : 'if card.human_gate != "none":'  -> L3464

PASS: the specified check reports all 728 drifted citations (521 repairable, 207 handed to a human); the bounds test it replaced reports 0.
```

The bounds test's recall is 0 of 728 — the blind region is the entire drifted
population, and its silence was indistinguishable from a clean deck. The anchor test
reaches 728 of 728 with no false positive on the 78 cites that are still correct,
which rules out the degenerate predicate that reports everything.

The population is larger than the 528 first reported on this card because the script
now maps both endpoints of range cites (`file.py:120-140`), as the shipped spec
requires; the recall figures are unchanged in shape.

A second, independent measurement over the working deck agreed before repair: of 181
citations that name a backticked identifier within 120 characters, 142 sat more than
40 lines from any occurrence of the symbol they named, while the `<= EOF` check
reported all 706 citations in the deck clean.

## Why it matters

The hygiene pass exists so a card stays readable cold, and a `file:line` cite is the
part a reader trusts most — it is precise, so it looks checked. A number that points
into the wrong function is worse than no number: it sends the next reader to code
that does not exhibit the defect, which reads as evidence the card is stale or wrong.
With 160 of 179 open cards parked at `human_gate: decision`, most cards here will be
read cold by someone who was not present when they were filed.

This is not local to this repo. The sentence ships in the packaged skill, so every
consuming repo's hygiene pass carries the same silent pass. The larger and
longer-lived the deck, the more citations it holds and the further its files have
moved — the check degrades exactly where it is most needed.

The rot class is already attested pointwise:
[sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop](../sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop/)
(closed) fixed one wrong engine line cite in a docstring. That was found by reading,
not by this check — consistent with a predicate whose recall on displacement is zero.

## Root cause it belongs to

This is an instance of
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/),
which names the shape: a fail-open check reports an empty offender list, and
nothing distinguishes "nothing is wrong" from "this check cannot see what is
wrong". That card's four instances are prohibition scanners in `tests/`; this one
is a sentence in a shipped skill, recorded there as a fifth surface because
neither of its options reaches a check that exists only as prose. The difference
worth carrying: those scanners could stop guarding, while this one never guarded —
measured recall 0 of 482 for the life of the deck.

Per that card's own convention for evidence connections on an open decision, the
link is a cross-reference and not an `advances` edge. The fix below is this card's
to carry regardless of how the scope question there is decided.

## Fix (shipped 2026-08-10)

The bounds test is gone from `goc/templates/skills/refine-deck/SKILL.md`
§ "Defunct file:line citations", replaced by the anchor test and the four-step
repair recipe below; the long form (why bounds fails, the resolution rules, the
residue table) went to that skill's `reference.md` § "Citation anchor check", and
all five mirrors were regenerated. The section now says outright that an in-range
line number is no evidence a cite is current, and that the cites the recipe declines
are reported for a human rather than skipped. `tests/test_skill_body_size.py` raised
the refine-deck cap from 10,300 to 11,200 bytes, with the rationale recorded there:
an agent that has to follow a pointer to learn the test will run the bounds test it
already remembers.

The recipe is not hypothetical: the 2026-08-10 hygiene pass ran it over this deck and
repaired 388 citations across 113 of 179 open cards, leaving `uv run goc validate`
clean. The mechanism, per citation:

1. Resolve the cited path, accepting the bare-basename shorthand cards use in prose
   (`engine.py:N` means `goc/engine.py:N`), preferring a non-mirror match.
2. Find the card's creating commit
   (`git log --diff-filter=A -- <card>/README.md`, last entry).
3. Read the cited file at that commit and take the cited line's text.
4. Locate that exact text in HEAD. Rewrite the number **only** when the match is
   unique and the line is non-trivial (skip bare braces, blanks, and anything under
   ~12 characters, which match everywhere).

The uniqueness-and-substance guard is what makes it safe to apply unattended: on this
deck it declined 279 citations (135 trivial, 112 ambiguous, 32 whose text no longer
exists) rather than guess. Those are the residue the DoD asks the skill to report
instead of dropping — a cite whose line text was deleted outright often means the
defect itself was refactored away, which is the case the current section already
handles correctly ("close via `Skill(finish-card)` with a note fixed incidentally
by <commit-hash>").

Line-range cites (`file.py:120-140`) map both endpoints independently and are
rewritten only when both resolve.
