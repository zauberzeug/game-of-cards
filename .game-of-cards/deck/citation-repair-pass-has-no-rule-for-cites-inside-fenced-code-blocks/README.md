---
title: citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks
summary: "The refine-deck citation recipe told a pass to relocate a defunct file:line cite on a unique anchor match but said nothing about cites sitting inside a fenced code block, where the same rewrite either repairs a claim about current code or falsifies a recorded transcript. With no rule each pass invented one: the 2026-08-31 reading (skip every fenced cite) left 28 cites across 16 cards stale, and all 28 turned out to be code-excerpt labels that should have been repaired. Both SKILL.md and reference.md now scope a cite by what it CLAIMS — a comment label (a `#` or `//` marker before the cite) is repaired wherever it sits; a dated record (pasted `grep -n` output, a reproduce.py transcript, a quoted error) is left and its count reported apart from the step-4 declines."
status: done
stage: null
contribution: medium
created: "2026-08-31T02:12:55Z"
closed_at: "2026-09-01T05:04:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero with check 1 reporting the recipe is
        explicit — both `refine-deck/SKILL.md` § "Defunct file:line citations"
        and `refine-deck/reference.md` § "Citation anchor check" name the
        fenced-block case.
  - [x] MECHANICAL: the recipe states which fenced cites are in scope and
        which are not, in terms a pass can apply without re-deriving the
        census — a cite that addresses current code is repaired wherever it
        sits; a cite that is part of a dated record is left and reported.
  - [x] MECHANICAL: the 17 pasted-tool-output cites the census finds are
        given an explicit disposition in the recipe, so a later pass does not
        read the silence as permission to rewrite them.
  - [x] MECHANICAL: mirrors re-synced (`pre-commit run --all-files`) and the
        OpenClaw port re-run (`python3 scripts/port_skills_to_openclaw.py`);
        `python3 scripts/port_skills_to_openclaw.py --check` is clean.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and
        `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---
# Citation repair pass has no rule for cites inside fenced code blocks

## Location

- `goc/templates/skills/refine-deck/SKILL.md:103-141` — § "Defunct file:line
  citations", the recipe a hygiene pass follows. Now opens with the scope
  paragraph, ahead of the four numbered steps.
- `goc/templates/skills/refine-deck/reference.md:123` — § "Citation anchor
  check" → **Scope: what the cite claims, not where it sits.**, the long form
  the recipe defers to.

Both name the fenced-block case; neither did when this card was filed.

## What's broken

The recipe is written as though every cite sits in prose. Step 4 says:

> Relocate the anchor text in HEAD and rewrite the number **only** on
> a unique match of a non-trivial line (>~12 chars, not a blank or a
> bare brace). Never guess.

That is a complete rule for *whether* a number can be relocated and no rule
at all for *whether it should be*. A cite inside a fenced block can be one of
two things, and they pull in opposite directions:

- **A comment label** — `# goc/engine.py:6202` sitting above a quoted
  snippet, or `for n in cmp.diff_files  # engine.py:1618` beside one. This is
  an assertion about where that code lives *now*. A stale number here is
  exactly the defect the recipe exists to fix, and leaving it unrepaired is
  the same failure as leaving a prose cite unrepaired.
- **Pasted tool output** — `goc/install.py:113:AGENTS_GUIDANCE = ...`, the
  `grep -n` format, reproduced as a record of what a command printed.
  Rewriting the number here fabricates output the command never produced. The
  card's evidence stops being evidence.

The recipe distinguished neither, so a pass had to invent a rule — and the
two defensible inventions disagree on every fenced cite in the deck.

## Empirical evidence

`uv run python .game-of-cards/deck/citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/reproduce.py`:

Before (at filing) check 1 counted 0 mentions on both surfaces and printed
`recipe is SILENT (defect fires)`. After the fix:

```
=== 1. does the shipped recipe mention fenced/code blocks? ===
  SKILL.md § Defunct file:line citations: 3 mention(s) of a fenced/code block
  reference.md § Citation anchor check: 6 mention(s) of a fenced/code block
  -> recipe is explicit (defect fixed)

=== 2. census: cites inside fenced blocks on open cards ===
  comment-label cites (`# path:line` above/beside quoted code): 49
  pasted-tool-output cites (`path:line:content`, no comment marker): 17
  spread over 31 open cards
```

Check 2 is a standing census, not a defect count — the shapes it separates
are what the new rule routes. All 17 pasted-output cites were re-read by
hand at closure: four transcript section headers on
`skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json`,
one `reproduce.py` "Cited code:" line, and twelve lines of `grep -n` output
across three cards. None is a comment label, so the marker test the recipe
now prescribes classifies the live corpus correctly with no exceptions.

## How the gap actually bit

The 2026-08-31 hygiene pass took the conservative reading — treat every
fenced cite as recorded evidence and skip it — on the reasoning that
corrupting a transcript is worse than leaving a number stale. It skipped 28
defunct cites across 16 cards on that basis.

Classifying those 28 afterwards showed the reasoning did not match the deck:
**all 28 were comment labels, and none was a transcript.** Every one of them
should have been repaired, and the pass had already computed a valid unique
relocation for each. They were then repaired in the same pass, which is why
the census above counts fenced cites rather than defunct ones: that pass
fixed the instances and left the recipe that produced them untouched, which
is what this card closed.

The opposite invention is equally reachable and worse: a pass that reads the
silence as "relocate everything" rewrites the 17 pasted-output cites and
leaves no trace that it did.

## Why it matters

Cite repair is permanent recurring work in this repo — see
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/),
which measured the 2026-08-24 pass at 95% decayed seven days later. A rule
that is re-invented on every pass is re-invented differently on every pass,
so the fenced subset would have oscillated between "always skipped" and
"always rewritten" depending on who ran it, with neither reading leaving a
record of the choice.

The recipe ships to every consuming repo, so the ambiguity was not local to
this deck — nor is the fix.

## Fix (applied)

The distinction is stated in the recipe, on both surfaces, as a scope filter
that runs before the anchor walk rather than as a caveat on step 4 — an
out-of-scope cite should not cost a `git log --follow` walk to skip:

- A cite is **in scope wherever it sits** — prose or fence — when it
  addresses current code. The fenced form is a **comment label**: a `#` or
  `//` marker before the cite on its line. Repaired by the same recipe.
- A cite is **out of scope and reported** when it is part of a dated record:
  pasted `grep -n` output in `path:line:content` form, a `reproduce.py`
  transcript, a quoted error message. Its count is reported under a heading
  of its own — apart from the step-4 declines, because a decline is a repair
  the pass *could* not make while an out-of-scope cite is one it *must* not.
- Undecidable → treat as a record. A stale label costs a reader one lookup;
  a rewritten transcript costs the card its evidence.

The core skill carries the rule and the marker test; the census, the failed
2026-08-31 pass and the reporting shape went to the reference sibling. A
pointer would not have worked here for a sharper reason than the three
earlier `refine-deck` cap raises: the defect *is* a pass inventing the
missing rule instead of going to look for it. `refine-deck`'s
`BODY_CAPS` entry in `tests/test_skill_body_size.py` moved 11,500 → 12,300
to fit it, with the rationale recorded there in the established form.

`tests/test_refine_deck_citation_anchor.py` gained
`DocumentedFencedScopeTest`, which classifies the shipped prose on each
surface into `SILENT` / `BLANKET` / `SPLIT_BY_CLAIM` rather than grepping
for keywords, asserts both surfaces reach the same verdict, and requires
each to give the mechanical marker test and not just the shape's name.
Replayed against the pre-fix prose at `HEAD~`, both surfaces classify
`SILENT` — the guard fails on the defect it was written for.

Note that this interacts with the open decision on
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/):
if that card adopts a self-anchoring citation form, the fenced/prose split
stops mattering for new cites but still governs the corpus already written.
Filed without an edge to it, per the schema's governing-cluster shape — that
card closes when *decided*, independently of this one.
