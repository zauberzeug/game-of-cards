---
title: regression-suite-red-on-main-over-the-unverified-tag-row
summary: "CI on main is red: `tests/test_canonical_tag_rows.test_live_cards_satisfy_every_state_row` fails because the live card `openclaw-pattern-check-never-fires-on-plain-file-edits` carries the `unverified` tag while shipping a working `reproduce.py`. The tag's `state` row scores `unverified` as \"no working reproduce.py\", but the card's DoD uses the tag to mean \"a load-bearing external premise is unconfirmed\" — the OpenClaw SDK's real edit-tool names — which its reproduce.py deliberately does not settle. The guard forbids widening the row to make this pass, so a human picks: retag the card, or split the row's meaning."
status: open
stage: null
contribution: high
created: "2026-08-06T05:37:37Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`.
  - [ ] TDD: `reproduce.py` exits zero — every live card satisfies every `state` row.
  - [ ] TDD: `uv run python -m unittest tests.test_canonical_tag_rows` passes, and `test_each_state_scorer_rejects_an_offender` still demonstrates the `unverified` scorer discriminates (a row change must not blunt it into always-true).
  - [ ] MECHANICAL: the chosen option landed — either the card's `tags` edited, or the `unverified` row rewritten in `goc/templates/skills/card-schema/SKILL.md` with its scorer in `tests/test_canonical_tag_rows.py` moved in lockstep and the mirrors re-synced.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# CI is red on main: a reproduced card tagged `unverified` fails its own row

## Location

- Failing test: `tests/test_canonical_tag_rows.py:189`
  (`test_live_cards_satisfy_every_state_row`).
- Scorer: `tests/test_canonical_tag_rows.py:106-113` (`_score_unverified`).
- Offending card:
  [openclaw-pattern-check-never-fires-on-plain-file-edits](../openclaw-pattern-check-never-fires-on-plain-file-edits/),
  filed 2026-08-04, `tags: [bug, infra, api-contract, unverified]`.

## What's broken

The suite is red on `main` as of commit `1ed2ddb2`. `.github/workflows/ci.yml`
runs `uv run python -m unittest discover -s tests`, so every subsequent CI run
on every Python version in the matrix fails until this is settled.

The `unverified` row is classified `state` — mechanically scoreable from card
state alone — and its scorer reads
(`tests/test_canonical_tag_rows.py:106-113`):

```python
def _score_unverified(card) -> bool:
    """`unverified` | no working `reproduce.py` AND tagged at filing.

    Only the first clause is card state; "tagged at filing" needs git history
    and is left to the author. A present-but-empty script is not working.
    """
    script = Path(card.path) / "reproduce.py"
    return not (script.exists() and script.stat().st_size > 0)
```

The offending card ships a 5,886-byte `reproduce.py` that runs and prints its
verdict, so the row fails. But the card's own DoD says the tag tracks something
the script was never meant to settle:

```
- [ ] EMPIRICAL: OpenClaw's actual file-edit tool names enumerated from the
  installed SDK (recipe in `## Falsification recipe`), verdict recorded in
  log.md either way — this is what clears the `unverified` tag
```

Its `reproduce.py` proves the *code shape* — that `openclaw-plugin/index.ts`
aliases the shell tool across hosts but hard-codes Claude Code's three edit-tool
names — and is explicit that the OpenClaw-native spellings it tries are guesses.
So the card is reproduced in one sense and unverified in another, and the row
recognises only the first.

## Empirical evidence

`uv run python .game-of-cards/deck/regression-suite-red-on-main-over-the-unverified-tag-row/reproduce.py`:

```
live cards scored: 186
state rows scored: ['bug', 'epic', 'unverified']
offenders: [('openclaw-pattern-check-never-fires-on-plain-file-edits', 'unverified')]

card    : openclaw-pattern-check-never-fires-on-plain-file-edits
tags    : ['bug', 'infra', 'api-contract', 'unverified']
row     : `unverified` scores as 'no working reproduce.py'
evidence: reproduce.py exists=True size=5886B -> row FAILS
card DoD: - [ ] EMPIRICAL: OpenClaw's actual file-edit tool names enumerated from the installed SDK (recipe in `## Falsification recipe`), verdict recorded in log.md either way — this is what clears the `unverified` tag

FAIL: the regression suite is red on main.
```

Verified pre-existing: the same failure reproduces in a detached worktree at
`1ed2ddb2`, the commit that filed the card, so it is not a side effect of any
later work.

## Why it matters

A red suite on `main` is a stop-the-line condition for this repo's autonomous
loop specifically. `Skill(finish-card)` closures routinely carry a
`PROCESS: the regression suite passes` DoD item, so every card closed while this
stands either blocks on an unrelated failure or gets its box ticked against a
suite that is not green — which is how a real regression slips through unnoticed.

The deeper reason this is worth a deliberate pick rather than a quick edit is
in the guard's own docstring. The `state`/`judgment` split exists because three
previous attempts widened a row's predicate to make a sweep pass, and each time
the widened row stopped discriminating. The test message says so outright:

> Either the card is mistagged or the row is wrong — pick one deliberately. Do
> not widen the row to make this pass; that is the move that failed three times.

This card is the fourth encounter with that fork, and this time the two readings
are genuinely balanced rather than one being an obvious dodge.

## Decision required

**Which of the two exits does this take?**

**Option A — the card is mistagged.** Drop `unverified` from
`openclaw-pattern-check-never-fires-on-plain-file-edits`. The row keeps its
sharp, mechanical meaning ("no working reproduce.py"); the card's unconfirmed
premise is already carried by its own unticked `EMPIRICAL:` DoD item, which is
arguably where an unverified *premise* belongs rather than in a tag.
*Cost:* the deck loses the ability to flag "reproduced, but resting on an
unconfirmed external fact" — `goc --tag unverified` stops surfacing this card,
and a reader has to open it to learn the premise is a guess.

**Option B — the row is too narrow.** Rewrite the `unverified` row so it also
covers a card whose reproduction is real but whose load-bearing external premise
is unconfirmed, and move `_score_unverified` in lockstep
(`test_state_rows_and_scorers_are_in_lockstep` enforces the pairing).
*Cost:* "external premise unconfirmed" is not readable out of card state, so the
row would likely have to be demoted from `state` to `judgment` — which drops it
out of `STATE_SCORERS` and out of CI enforcement entirely. That is the exact
blunting the guard was built to prevent, and
`test_each_state_scorer_rejects_an_offender` is the check that would have to keep
holding.

Option A is a one-line frontmatter edit; Option B changes what a shipped
canonical tag means for every consuming repo, so it also needs the
`card-schema` skill body edited and the four mirrors re-synced.

**Not a third option:** silently widening `_score_unverified` (e.g. also
accepting a card whose DoD mentions the tag) while leaving the row classified
`state`. That is the move the guard names and forbids.
