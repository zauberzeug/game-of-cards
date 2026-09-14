---
title: citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank
summary: "The citation anchor recipe applies its non-triviality guard only when relocating a defunct cite, never when deciding whether the cite is defunct at all. The compare step tests raw line equality, so a cite whose anchor text is a bare brace, a blank line, or 'return 0' verdicts 'current' whenever HEAD happens to carry the same token at that offset — the silent false-clean the recipe was written to replace. Measured on this deck 2026-09-14: 46 of 413 'current' verdicts (11%), across 28 open cards, rest on such an anchor; two are provably wrong."
status: open
stage: null
contribution: medium
created: "2026-09-14T02:10:56Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no `current` verdict over the open/active deck rests on a line the recipe's own step-4 predicate calls unusable.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" applies the trivial-line predicate at the DECIDE step, not only at the relocate step, and `SKILL.md`'s condensed recipe carries the same clause at its step 3.
  - [ ] MECHANICAL: that section's residue table gains the new decline reason, so the shape is reported rather than absorbed into `current`.
  - [x] EMPIRICAL: the two cites named as provably wrong in the transcript above are re-derived from their own cards' prose, corrected, and the correction recorded in each card's `log.md`. Done 2026-09-14 in the pass that filed this card.
---

# Citation repair pass calls a cite `current` when its anchor line is a brace or blank

## Location

- `goc/templates/skills/refine-deck/reference.md` — § "Citation anchor check",
  the **Deciding** paragraph. Mirrored to consumers at
  `.claude/skills/refine-deck/reference.md`, `claude-plugin/skills/…`,
  `codex-plugin/skills/…`, `openclaw-plugin/skills/…`.
- `goc/templates/skills/refine-deck/SKILL.md` — § "Defunct file:line
  citations", the condensed four-step recipe (steps 3 and 4).

## What's broken

The recipe decides in two steps and guards only the second one. Step 3 asks
whether the cite is defunct:

> Anchor text ≠ the text at that line in HEAD → defunct.

Step 4 then relocates a defunct cite, and *there* the recipe demands substance:

> Then look for the anchor text in HEAD and rewrite the number only when the
> match is UNIQUE and the line is NON-TRIVIAL: skip blanks, bare braces, and
> anything under roughly 12 characters, **which match everywhere**.

The final clause is the reason the guard exists, and it is just as true one
step earlier. Step 3's equality test is `anchor == head[N]` with no predicate
on what that text is, so a cite whose anchor line is `}` is pronounced
`current` whenever HEAD also holds `}` at offset N. In a brace-dense or
blank-line-dense file that is the ordinary case, not the exception.

The asymmetry is what makes it a defect rather than a rough edge. A trivial
anchor is refused as evidence *for* a rewrite and accepted as evidence
*against* one — so the same line that is too weak to move a cite by one line
is strong enough to certify it for another pass.

## Empirical evidence

`reproduce.py` replays the recipe over every in-scope cite in the open and
active deck and reports each `current` verdict resting on a line step 4 would
refuse:

```
`current` verdicts over open/active cards : 413
  ...resting on a trivial anchor line     : 46  over 28 cards

  goc/engine.py:144                  anchor=''             file-line-citations-drift-again-within-days-of-every-repair-pass
  goc/engine.py:96-103               anchor='pass'         unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
  goc/engine.py:3641-3642            anchor='return ""'    ready-leverage-line-goes-silent-when-no-card-is-pullable
  openclaw-plugin/index.ts:749-762   anchor='});'          deck-prompt-router-exploration-and-tooling-lists-can-never-suppress-the-reminder
  goc/__init__.py:7-17               anchor='pass'         vendored-engine-reports-co-installed-distribution-version-not-its-own
  …40 more
```

Eleven percent of the verdicts the pass reports as verified carry no evidence.
Most of them are probably right — the `unguarded-loader-…` row above lands
exactly on the block its card quotes. That is the problem: the pass cannot tell those from
the ones that are wrong, and it reports both the same way.

**Two are provably wrong.** Mapping each anchor commit's file onto HEAD with a
line-level diff shows where the anchored line actually went:

```
cite                    card                                            anchor line moved
engine.py:1722          goc-waiting-filter-drifts-from-engine-…         1722 -> 2552
goc/engine.py:42-120    openclaw-resolve-deck-dir-ignores-git-…         42 -> 43, 120 -> 144
```

Every cite token this card carries is a **dated record** of a number some other
card holds, not an assertion about where code lives now — repairing them would
destroy the measurement this card was filed to carry. They are kept in fenced
transcripts so the recipe's own scope rule classifies them correctly.

The first row is the worked example, and it is worse than drift. The card's
prose reads:

```
next /loop tick because `card_is_ready` (`engine.py:1722`) returns
```

At the anchor commit — `5570bdb4`, the card's own filing commit —
`card_is_ready` was at line **1729**. Line 1722 was blank, two lines above an
unrelated function. The cite was wrong the day it was authored. In HEAD,
`card_is_ready` is at line **2632** and line 1722 is still blank, sitting
inside plugin-mirror code that has nothing to do with readiness. So the anchor
is `""`, HEAD's line 1722 is `""`, the texts match, and three consecutive
anchored passes have certified a cite that misses its named function by 910
lines and never named it correctly at all.

A blank anchor cannot decay, which is exactly why it is the worst kind: it
freezes the author's original typo into a permanent `current`.

Both wrong cites were repaired by hand in the pass that filed this card — each
card's own prose names the symbol it meant, so the address was recoverable even
though no mechanical rule could recover it. The transcript above is kept as the
measurement, not as a live defect list. What is *not* fixed is the reason they
survived three passes undetected, which is what this card is for.

## Why it matters

This is the same failure shape as the bounds test the anchored recipe was
written to replace, and the reference is explicit about why that one was fatal:
its silence was indistinguishable from a clean deck for the life of the deck.
A `current` verdict is silence — it produces no output, no decline line, no
residue-table row. The declines are read; the certifications are not, because
there is nothing to read.

The blast radius is every consumer, not just this repo: `refine-deck` ships in
all four plugin payloads, and the recurring hygiene pass is the only thing that
re-checks a cite after it is written.

This is the fifth instance of "the recipe's rule for one step was missing or
wrong", after
[refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/)
(the bounds test),
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
(the anchor commit),
[citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks](../citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/)
(scope), and
[citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range](../citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range/)
(range pairing). All four fixed the relocate side. None looked at the decide
side. Two siblings filed the same round:
[citation-repair-pass-declines-a-moved-function-whose-definition-line-gained-a-parameter](../citation-repair-pass-declines-a-moved-function-whose-definition-line-gained-a-parameter/)
and
[citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide](../citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide/).

The addressing convention itself is a separate, gated question —
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
prices the options for replacing bare line numbers. This card does not depend
on that pick: whatever form is chosen, a verdict that rests on a brace is
worthless under it too.

## Fix

Apply step 4's own predicate at step 3. A cite whose anchor line is trivial
cannot be decided by text equality in either direction, so the honest verdict
is neither `current` nor `repair` — it is a decline, reported in the residue
table beside the three that already exist:

| Decline | What it usually means |
|---|---|
| **trivial anchor, verdict undecidable** | the anchor line is a blank, a bare brace, or under ~12 characters, so matching it at the cited offset is not evidence the cite is current; a reader must re-derive the address from the card's prose |

Concretely, in `reference.md` § "Citation anchor check", the **Deciding**
paragraph becomes: refuse the comparison first — if the anchor line is trivial,
report and stop; only then compare, and only then relocate. `SKILL.md`'s step 3
gains the same clause in its condensed form. Both files are mirrored, so the
edit lands once in `goc/templates/skills/refine-deck/` and the pre-commit sync
propagates it.

Cost: 46 cites move from a false `current` into the reported residue in the
first pass after the fix, which is the correct accounting rather than a
regression. The two known-wrong ones are repaired by hand as part of this
card's DoD, since no mechanical rule can recover an address its author never
wrote correctly.

## Non-goals

- Changing the addressing convention (bare `file:line` vs. symbol-relative vs.
  self-anchoring). That is the gated decision on
  `file-line-citations-drift-again-within-days-of-every-repair-pass`.
- Relaxing the relocate-step guard. That is the sibling card.
- Auto-repairing the 44 unprovable cases. They become reported residue; a
  reader decides.
