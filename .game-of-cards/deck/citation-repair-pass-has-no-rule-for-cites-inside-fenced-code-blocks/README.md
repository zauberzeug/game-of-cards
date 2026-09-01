---
title: citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks
summary: "The refine-deck citation recipe tells a pass to relocate a defunct file:line cite on a unique anchor match, but says nothing about cites that sit inside a fenced code block, where the same rewrite can either repair a claim about current code or falsify a recorded transcript. With no rule, a pass must invent one: this round's conservative reading (skip all fenced cites) left 28 cites across 16 cards stale, and a census showed all 28 were in fact code-excerpt labels that should have been repaired. The recipe needs to say which fenced cites are in scope."
status: active
stage: null
contribution: medium
created: "2026-08-31T02:12:55Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero with check 1 reporting the recipe is
        explicit — both `refine-deck/SKILL.md` § "Defunct file:line citations"
        and `refine-deck/reference.md` § "Citation anchor check" name the
        fenced-block case.
  - [ ] MECHANICAL: the recipe states which fenced cites are in scope and
        which are not, in terms a pass can apply without re-deriving the
        census — a cite that addresses current code is repaired wherever it
        sits; a cite that is part of a dated record is left and reported.
  - [ ] MECHANICAL: the 17 pasted-tool-output cites the census finds are
        given an explicit disposition in the recipe, so a later pass does not
        read the silence as permission to rewrite them.
  - [ ] MECHANICAL: mirrors re-synced (`pre-commit run --all-files`) and the
        OpenClaw port re-run (`python3 scripts/port_skills_to_openclaw.py`);
        `python3 scripts/port_skills_to_openclaw.py --check` is clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and
        `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---
# Citation repair pass has no rule for cites inside fenced code blocks

## Location

- `goc/templates/skills/refine-deck/SKILL.md:103-124` — § "Defunct file:line
  citations", the four-step recipe a hygiene pass follows.
- `goc/templates/skills/refine-deck/reference.md:111` — § "Citation anchor
  check", the long form the recipe defers to.

Neither mentions a fenced code block.

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

Because the recipe distinguishes neither, a pass has to invent a rule, and
the two defensible inventions disagree on every cite in the deck.

## Empirical evidence

`uv run python .game-of-cards/deck/citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/reproduce.py`:

```
=== 1. does the shipped recipe mention fenced/code blocks? ===
  SKILL.md § Defunct file:line citations: 0 mention(s) of a fenced/code block
  reference.md § Citation anchor check: 0 mention(s) of a fenced/code block
  -> recipe is SILENT (defect fires)

=== 2. census: cites inside fenced blocks on open cards ===
  comment-label cites (`# path:line` above/beside quoted code): 50
  pasted-tool-output cites (`path:line:content`, no comment marker): 17
  spread over 32 open cards
```

## How the gap actually bit

The 2026-08-31 hygiene pass took the conservative reading — treat every
fenced cite as recorded evidence and skip it — on the reasoning that
corrupting a transcript is worse than leaving a number stale. It skipped 28
defunct cites across 16 cards on that basis.

Classifying those 28 afterwards showed the reasoning did not match the deck:
**all 28 were comment labels, and none was a transcript.** Every one of them
should have been repaired, and the pass had already computed a valid unique
relocation for each. They were then repaired in the same pass, which is why
the census above counts fenced cites rather than defunct ones — the specific
instances are fixed, the recipe that produced them is not.

The opposite invention is equally reachable and worse: a pass that reads the
silence as "relocate everything" rewrites the 17 pasted-output cites and
leaves no trace that it did.

## Why it matters

Cite repair is permanent recurring work in this repo — see
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/),
which measured the 2026-08-24 pass at 95% decayed seven days later. A rule
that is re-invented on every pass is re-invented differently on every pass,
so the fenced subset oscillates between "always skipped" and "always
rewritten" depending on who ran it, and neither reading leaves a record of
the choice.

The recipe ships to every consuming repo, so the ambiguity is not local to
this deck.

## Fix

State the distinction in the recipe. The census supports a rule that is
cheap to apply and does not require classifying prose:

- A cite is **in scope wherever it sits** — prose or fence — when it
  addresses current code. A comment label (`#` / `//` marker preceding the
  cite on its line) is the fenced form of that.
- A cite is **out of scope and reported** when it is part of a dated record:
  pasted command output, a `reproduce.py` transcript, a quoted error message.

Both `SKILL.md` § "Defunct file:line citations" step 4 and `reference.md`
§ "Citation anchor check" need the sentence; the SKILL.md copy is the one a
pass reads first.

Note that this interacts with the open decision on
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/):
if that card adopts a self-anchoring citation form, the fenced/prose split
stops mattering for new cites but still governs the corpus already written.
Filed without an edge to it, per the schema's governing-cluster shape — that
card closes when *decided*, independently of this one.
