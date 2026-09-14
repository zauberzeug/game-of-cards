---
title: citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide
summary: "The anchor walk finds a cite's anchor commit by asking when the cite token turns from absent to present in the card README, but a token is not unique within a card. A cite whose number is a substring of a range cite, or that a past repair moved onto a number another cite already held, inherits that other cite's anchor and is then reported as drifted when it is correct. The 2026-09-14 pass caught three such phantom repairs on an idempotence re-run the recipe does not ask for; applying them would have moved three correct cites onto wrong lines."
status: active
stage: null
contribution: medium
created: "2026-09-14T02:10:56Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the token walk and the occurrence-aware walk agree on the anchor commit for every in-scope cite in the open/active deck.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" makes the presence test token-exact rather than substring, and declines a cite whose token appears at more than one in-scope occurrence in its card; `SKILL.md`'s step 2 carries both in condensed form.
  - [ ] MECHANICAL: that section's residue table gains the ambiguous-occurrence decline reason.
  - [ ] PROCESS: the skill's citation step ends with an idempotence check — re-run the decision phase after applying and assert zero repairs remain — since that is what surfaced this class and no per-cite rule catches it.
worker: {who: "claude[bot]", where: main}
---

# Citation repair pass gives two cites in one card the same anchor when their numbers collide

## Location

- `goc/templates/skills/refine-deck/reference.md` — § "Citation anchor check",
  the **Getting the anchor** paragraph. Mirrored to consumers at
  `.claude/skills/refine-deck/reference.md`, `claude-plugin/skills/…`,
  `codex-plugin/skills/…`, `openclaw-plugin/skills/…`.
- `goc/templates/skills/refine-deck/SKILL.md` — § "Defunct file:line
  citations", step 2 of the condensed recipe.

## What's broken

The recipe locates a cite's anchor commit by walking the card's own history:

> read the README at each commit, and take the newest commit at which the
> exact cite token turns from absent to present

The cite **token** is the entire identity. Nothing ties the walk to the
occurrence being repaired, and a token is not unique inside a card. Two ways
that breaks, both measured on this deck:

**Substring collision.** A single-line cite `path:N` occurs inside a range cite
`path:N-M` written in the same card. A plain presence test reads the shorter
token as already present at every commit the range existed, so the walk never
sees it "turn from absent to present" at the commit that actually wrote it, and
falls back to the range's older anchor.

**Convergence.** A repair pass moves cite A onto the number cite B already
holds — routine, since neighbouring cites drift by the same amount. From that
commit on, the two occurrences are one token with one history, and the walk
cannot give them different anchors even in principle. Occurrence-awareness in
the presence test does not help here; the walk has no notion of *which*
occurrence at all.

Either way the cite is anchored on text it never named. Compared against HEAD
it reads defunct while being correct, and step 4 then relocates it onto the
line that other cite's anchor text now occupies.

## Empirical evidence

The hygiene pass of 2026-09-14 repaired 229 cites and then re-ran itself to
check idempotence. A correctly repaired deck must produce zero repairs on the
second run. It produced three, all on cites the same pass had just written
correctly:

```
deck-auto-commit-ignores-card-files-other-than-readme-and-log
    goc/engine.py:4969 -> 4970    (convergence)
closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded
    goc/engine.py:5200 -> 5201    (substring collision with goc/engine.py:5200-5206)
goc-status-active-drops-prior-worker-where-on-detached-head-reclaim
    goc/engine.py:5844 -> 5845    (substring collision with goc/engine.py:5844-5849)
```

All three are false. Each cite names a function; HEAD holds that function's
`def` line at exactly the cited number; the proposed rewrite moves it one line
down onto the docstring. `reproduce.py` runs the walk both ways and shows the
anchors the two readings pick:

```
cites whose two walks disagree about the anchor commit: 2  over 2 cards

  goc/engine.py:5200         closure-on-integration-check-only-runs-for-done-not-
      token walk  -> a990a8497  anchor '"""When workflow.closure_on_integration is enabled, refuse c'
      occurrence  -> 278ff831c  anchor 'def _enforce_closure_on_integration_or_exit(title: str) -> N'
      HEAD line   ->            'def _enforce_closure_on_integration_or_exit(title: str) -> N'   (would be 'repaired' onto a wrong line)

population at risk — cards holding one in-scope cite token at two or more
occurrences, where the walk cannot give the occurrences different anchors
even in principle: 63
```

The convergence case is the one the script cannot flag, and it is worth being
explicit about why: at the earlier commit the token genuinely was present, at a
different occurrence, so no presence test distinguishes it. It is reported here
from the pass transcript instead. The at-risk population is 63 cards — benign
today, because both occurrences of a repeated token still mean the same line,
and one repair away from not being.

Every cite token above is a dated record of the measurement, not an assertion
about where code lives now, and is kept fenced so the recipe's own scope rule
classifies it correctly.

## Why it matters

This one does not merely mis-verdict — it **writes**. The other two recipe gaps
found the same round either accept weak evidence
([citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank](../citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank/))
or refuse good evidence
([citation-repair-pass-declines-a-moved-function-whose-definition-line-gained-a-parameter](../citation-repair-pass-declines-a-moved-function-whose-definition-line-gained-a-parameter/)).
This one takes a correct cite and moves it. It is the same harm
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
closed — that card fixed *which commit* the walk should anchor on, and left
*which occurrence* unaddressed, so the same wrong-anchor outcome is still
reachable by a different route.

It is also self-concealing in the way that card described: once the cite has
been moved, the next pass anchors on the moved number and verdicts it `current`.
Nothing reports it afterwards. This pass caught it only because it re-ran for
idempotence, which the recipe does not ask for — so a pass following the recipe
exactly would have written all three and reported three successful repairs.

The shape is generated by the repair passes themselves: convergence happens
*because* neighbouring cites drift together and get corrected together. The
population grows with every pass.

## Fix

Two edits to `reference.md` § "Citation anchor check", both in **Getting the
anchor**:

1. **Make the presence test token-exact, not substring.** Extract the cite
   tokens from each historical version with the same pattern the pass uses to
   find cites, and test set membership. `path:N` must not read as present
   inside `path:N-M`. This alone removes the substring half.
2. **Anchor per occurrence, not per token.** When a card holds one token at two
   or more in-scope occurrences, the walk cannot separate them; the honest
   answer is a decline, reported in the residue table under a new reason
   (*ambiguous occurrence — the same token appears more than once in this
   card*), not a rewrite.

A cheaper partial guard, worth stating because it is nearly free: **a cite that
already resolves at HEAD is never a repair candidate.** All three false repairs
had HEAD's line matching what the card's prose names. Checking that first would
have stopped every one of them, without any change to the walk. It is a
belt-and-braces rule rather than a fix — it silences the symptom for cites that
happen to be correct, and does nothing for a cite that is genuinely defunct and
gets anchored on a neighbour's history.

Add an idempotence check to the pass's own closing step: re-run the decision
phase after applying and assert zero repairs remain. That is what surfaced this
defect, and it is the only guard that catches the class rather than the two
instances.

## Non-goals

- Changing the addressing convention. That is the gated decision on
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/).
- Forbidding a card from citing the same line twice. The repetition is
  legitimate; the walk's inability to tell the occurrences apart is the defect.
- Retro-auditing past passes for cites already moved this way. Worth doing, but
  it needs the fixed walk first to have anything trustworthy to compare against.
