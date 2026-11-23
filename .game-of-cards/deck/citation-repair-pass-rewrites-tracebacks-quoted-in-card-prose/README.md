---
title: citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose
summary: "FIXED 2026-11-23: the refine-deck citation scope rule's only mechanical record test, the comment-marker test, reads fenced lines only, so a traceback frame quoted in a prose bullet on repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field read as a cite about current code and was renumbered by all four passes that ran after the rule shipped. The scope rule (SKILL.md and reference.md) now says a record quoted in prose is still a record, which the pass moves into a fence with its numbers as filed so the marker test holds it from then on, and create-card Step 5 puts quoted output in a fenced block from the start. The instance's result bullets are fenced as filed, and a classifier in the citation-anchor tests pins the rule."
status: done
stage: null
contribution: low
created: "2026-11-23T02:09:59Z"
closed_at: "2026-11-23T04:38:08Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no live card quotes a traceback or frame chain outside a fenced block.
  - [x] MECHANICAL: the dry-run and `--apply` result bullets on `repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field` move into a fenced block with their numbers as filed (`4954 → 4911`), so the existing marker test reads the frame as a record.
  - [x] MECHANICAL: the scope paragraph in `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations", and `reference.md` § "Citation anchor check" with it, say that a record quoted in prose is still a record, and that the pass moves it into a fence with its numbers unchanged, so the next pass's marker test protects it without a re-read.
  - [x] MECHANICAL: `goc/templates/skills/create-card/SKILL.md` Step 5 says pasted output (reproduce.py output, tracebacks, error text) goes in a fenced block, so new records are born where the test can see them.
  - [x] TDD: `tests/test_refine_deck_citation_anchor.py` classifies the shipped scope prose for the prose-record rule beside `documented_fenced_scope`, failing on today's text and passing after the edit.
  - [x] MECHANICAL: mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
  - [x] MECHANICAL: `tests/test_skill_body_size.py` raises the refine-deck cap 16,300 → 16,500 and the create-card cap 10,500 → 10,600, each with its reason; both skills sat at their caps (26 and 1 bytes of headroom), so the two rule sentences could not land otherwise.
worker: {who: "claude[bot]", where: main}
---

# The citation repair pass rewrites tracebacks quoted in card prose

## Location

- `goc/templates/skills/refine-deck/SKILL.md:143-153` — the scope rule of
  § "Defunct file:line citations", now with the prose case;
  `reference.md` § "Citation anchor check", paragraph "A record quoted in
  prose is still a record — and only a fence says so", is its long form.
- `goc/templates/skills/create-card/SKILL.md:159-161` — Step 5's "Empirical
  evidence" line, which now puts quoted output in a fenced block.
- `tests/test_refine_deck_citation_anchor.py` — `documented_prose_record_rule`
  and `DocumentedProseRecordRuleTest`, beside `documented_fenced_scope`.
- The instance: the "Live CLI confirmation" block under `## Empirical
  evidence` on
  [repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field](../repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field/),
  fenced since this fix.

## What was broken

The scope rule named three kinds of dated record and gave a test for only
one place a record can sit. As it shipped from 2026-09-01:

```text
Scope by what the cite CLAIMS, not by where it sits. A cite asserting
where code lives NOW is in scope in prose and inside a fenced block
alike — the fenced form is a COMMENT LABEL, a `#` or `//` marker before
the cite on its line. A cite that is part of a dated record — pasted
`grep -n` output (`path:line:content`), a `reproduce.py` transcript, a
quoted error — is OUT of scope: rewriting its number fabricates output
the command never produced. Repair the labels; leave the records and
report their count apart from the declines below. Undecidable → record.
```

Inside a fence the marker test decides: no `#` or `//` before the cite
means a record. Outside a fence the only test was the first sentence, which
calls a prose cite an assertion about where code lives now. "Undecidable →
record" helps only a pass that notices the line is undecidable. A quoted
result line written as a prose bullet does not look undecidable. The
instance's bullets, as filed:

```text
- `goc repair-edges` (dry run) → traceback ending `ValueError: advanced_by: not a list` at `engine.py:4954 → 4911`.
- `goc repair-edges --apply` → same traceback via `_cmd_repair_edges → _mutate_pair → 4911`.
```

The first frame of that chain, line 4954 of `engine.py`, is what the card's
author saw printed on 2026-06-23 — a record. To the rule's test it was a
backticked prose cite like any other. Its anchor is a real, unique line, so
every guard in the recipe passed and the pass moved it. The second frame,
`4911`, has no path in front of it, so no pass ever touched it: from
2026-08-10 to the 2026-11-16 restore, the card quoted a frame chain that no
traceback could print.

## Empirical evidence

`uv run python .game-of-cards/deck/citation-repair-pass-rewrites-tracebacks-quoted-in-card-prose/reproduce.py`,
on 2026-11-23 before the fix (exit 1):

```text
Live cards scanned: 193
Cites inside a quoted traceback or frame chain, in prose (outside fences and blockquotes): 1
  repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field L103: engine.py:4954
      - `goc repair-edges` (dry run) → traceback ending `ValueError: advanced_by: not a list` at `engine.py:4954 → 4

History of the frame quoted on repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field
(first number of `engine.py:N → M`; scope rule = eae2bea9):
  1368bb56 2026-06-23   4954 → 4911  as filed
  69e1e4f2 2026-08-10   5891 → 4911  rewritten before the scope rule
  f290f5f7 2026-08-17   6139 → 4911  rewritten before the scope rule
  e8449764 2026-08-24   6250 → 4911  rewritten before the scope rule
  9bad9881 2026-08-31   6300 → 4911  rewritten before the scope rule
  9d5bd88f 2026-09-07   6303 → 4911  rewritten AFTER the scope rule shipped
  278ff831 2026-09-14   6304 → 4911  rewritten AFTER the scope rule shipped
  9085ef04 2026-09-21   6356 → 4911  rewritten AFTER the scope rule shipped
  3ebd9b7e 2026-11-09   7165 → 4911  rewritten AFTER the scope rule shipped
  2a665b45 2026-11-16   4954 → 4911  restored to the filed number by hand
Rewrites after the rule shipped: 4

DEFECT PRESENT: a record quoted in prose is indistinguishable from a cite about current code under the scope rule's only test, so the next pass that does not read the line rewrites it.
```

Every pass that ran after the rule shipped rewrote the frame, four in a row.
The 2026-11-09 sweep that restored four fenced transcripts checked fenced
records only and missed it. The 2026-11-16 pass restored it by reading the
line. On 2026-11-23 the next pass's classifier, which implements the marker
test, proposed `4954 → 5074` in both its first round and its committed
re-run. Only a manual read held it. `5074` is a line in `_cmd_default`, which
`goc repair-edges` never reaches.

It was the only such line on the deck: the reproducer's scan over 193 live
cards found one.

After the fix, same day (exit 0; the replay rows above are unchanged, and
once the fix is committed the replay adds one row, for the commit that moved
the frame into a fence with its number as filed):

```text
Live cards scanned: 193
Cites inside a quoted traceback or frame chain, in prose (outside fences and blockquotes): 0
...
OK: no live card quotes a traceback or frame chain outside a fence.
```

Under the marker test as the scope rule words it, the instance's first
frame (`4954 → 4911`) now reads as a fenced record, out of scope. The new
classifier returns `prose-record-left-to-each-pass` for the scope prose at
`4bd2dbe4`, the commit before the fix (core skill and reference alike), and
`prose-record-moved-under-the-marker-test` for both after the edit.

## Why it mattered

A rewritten record is worse than a stale cite. A stale cite costs a reader
one lookup. A rewritten traceback frame claims the command printed something
it never printed, and a reader who re-runs the command to compare sees a
mismatch that looks like a behaviour change. The scope rule was written to
prevent exactly that
([citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks](../citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/),
closed 2026-09-01). It held wherever its test reached and failed silently
where it did not. Recognition had to happen on every pass, and four
consecutive passes did not do it.

## Fix (applied)

Prose records are made reachable by the test that already works, rather
than by a second test:

1. **The instance.** The three "Live CLI confirmation" result bullets on
   `repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field`
   sit in a `text` fence, numbers as filed (`4954 → 4911`), wording
   unchanged except for the inline-code markup, which a fence would print
   literally. The third bullet (`goc advance`) went with the other two
   because the three are one record. A log entry on that card says why;
   its defect and gate are untouched.
2. **The scope rule.** `refine-deck/SKILL.md` adds one sentence to the
   scope paragraph — a record quoted in prose is still a record: move it
   into a fence with its numbers as filed, so the next pass's marker test
   holds it without a re-read — and "Undecidable → record" becomes
   "Undecidable → record, left in place". `reference.md` gains the long
   form beside the fenced-scope census: why prose escapes the marker test,
   this instance's history, the move, the reporting, and the rejected
   keyword test.
   - "As filed" is how the rule words this card's "numbers unchanged". The
     pass does not renumber the record, and a number an earlier pass already
     rewrote is restored from the card's history before it is fenced,
     because a fence around a renumbered frame would protect the
     fabrication. This card's own instance had been rewritten four times
     before its hand restore.
   - An undecidable prose cite stays where it sits. Fencing it would take a
     cite that may be a label out of every later pass's reach for good.
3. **Authoring.** `create-card/SKILL.md` Step 5: quoted output
   (`reproduce.py`, tracebacks, error text) goes verbatim in a fenced block,
   so no citation pass renumbers it. New records start where the test
   reaches them.
4. **The guard.** `documented_prose_record_rule` reads the sentence that
   carries the rule. That sentence has to name the prose case, the move into
   a fence, the numbers as filed (or unchanged) and the marker-test reason.
   A section-wide phrase check would pass vacuously, because the reference
   says "as filed" twice for its anchor walk. Six tests cover it: the core
   skill and the reference, the shipped paragraph classified as unreached,
   two weaker rules refused (a record recognised but left in prose, and one
   fenced only after its numbers moved), and prose with no scope rule
   unclassifiable.
5. **Caps.** Both SKILL.md files were at their `tests/test_skill_body_size.py`
   caps, so the caps were raised with recorded reasons: refine-deck
   16,300 → 16,500 (taxed size 16,440) and create-card 10,500 → 10,600
   (10,588).
6. **Reproducer.** Its replay regex accepts the fenced form (no inline-code
   backticks), and the replay reports the move into a fence. The scan that
   decides the exit code is unchanged.

Rejected: a keyword test for prose (`traceback`, `→`, "printed"). It would
catch this line and nothing proves it catches the next one, and it would
leave the classification a per-pass judgment. The fence is already the one
marker every pass applies mechanically.

