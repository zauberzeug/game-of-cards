---
title: card-language-guard-still-flags-legitimate-english-its-docstring-rules-out
summary: "UNVERIFIED. scripts/check_card_language.py says every marker word is never legitimate English, that eight of its nine German suffixes have no English collision, and that no future prefix can create a new -ung false positive; yet flag_text flags seven common English words (listed in the body, not here, because this field is scanned): four marker-list homographs, one word on a supposedly collision-free suffix, and two -ung words whose prefix the enumerated prefix set lacks. The guard runs as a pre-commit hook and in CI, so an English card title can fail the build."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:39:06Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, test, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py feeds `flag_text` the seven English words quoted in this card's Hypothesis section and asserts none is flagged — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: `tests/test_card_authoring_rules.py` asserts clean verdicts for English words outside the guard's own prefix × stem literals (at least one prefix not in `ENGLISH_UNG_PREFIXES`, one word on a suffix the docstring calls collision-free, one marker-list homograph), so the property the docstrings claim is tested rather than restated
  - [ ] MECHANICAL: the docstring claims at `scripts/check_card_language.py:49-50`, `:101-104`, `:147-148` and `:160-162` match the guard's actual behavior; drop the `unverified` tag once reproduce.py lands; append a post-close pointer to `card-language-guard-flags-legitimate-english-as-non-english/log.md`
---

# The card-language guard still flags legitimate English its docstring rules out

> **UNVERIFIED.** Surfaced by an audit hunter on the repo-scripts-and-CI
> seam on 2026-09-28. The filing agent re-read the citations and re-ran
> `flag_text`. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

All in `scripts/check_card_language.py`:

- `:101-104`: "Every entry is a claim that its appearance in a card is a
  language slip and never legitimate English". Yet the French list
  (`:120`, `:123`) carries `tout` and `nouveau`, and the Spanish or Portuguese
  list (`:127`) carries `algo` and `nada`. All four are in English use:
  - `tout` is an English noun and verb;
  - `nouveau` as in *art nouveau*;
  - `algo` is everyday engineering shorthand for "algorithm";
  - `nada` is informal English.
- `:49-50` and `:147-148`: "Eight of the nine [suffixes] have no English
  collision at any length". But `-heit` (`MARKER_SUFFIXES`, `:151`)
  matches *fahrenheit*.
- `:160-162`: "English has no productive `-ung` suffix, so the stem set is
  closed … and no future prefix combination can become a new false
  positive." The stems are closed, but the prefixes are an enumeration
  of seven (`ENGLISH_UNG_PREFIXES`, `:167`). Any English word built on a
  listed stem with an unlisted prefix is flagged: *hamstrung*,
  *underhung*.
- `tests/test_card_authoring_rules.py:319-330`
  (`test_exemption_composes_beyond_the_source_literals`) composes only
  the listed prefixes with the listed stems. It therefore cannot see an
  unlisted prefix, which is the exact gap `:160-162` says cannot exist.

## Hypothesis

The guard rejects ordinary English that its own docstrings promise it
accepts. The filing agent ran `flag_text` and got:

```
'retry budget is hamstrung by a fixed cap' -> ["German '-ung' ending on token 'hamstrung'"]
'underhung rotor' -> ["German '-ung' ending on token 'underhung'"]
'convert fahrenheit to celsius' -> ["German '-heit' ending on token 'fahrenheit'"]
'the tout for the new release' -> ["French marker word 'tout'"]
'art nouveau styling in the site' -> ["French marker word 'nouveau'"]
'the algo is fine' -> ["Spanish or Portuguese marker word 'algo'"]
'nada happens' -> ["Spanish or Portuguese marker word 'nada'"]
```

This card quotes the seven words only here in the body, which the guard
does not scan. The first draft of this card named them in its summary
and DoD, and the guard reported 14 findings against it. That near-miss
is itself evidence.

This is reachable from ordinary authoring. The guard runs as the
`card-language` pre-commit hook (`.pre-commit-config.yaml`) and in CI via
`test_live_deck_is_clean`. The hunter showed that a card titled
`retry-budget-is-hamstrung-by-a-fixed-cap` makes `--check` exit 1 with 3
findings and fails that test. `algo` in particular is likely in an
engineering deck's summaries.

This is post-close evidence on
[card-language-guard-flags-legitimate-english-as-non-english](../card-language-guard-flags-legitimate-english-as-non-english/)
(done). Its README (lines 204-207) records the "eight endings have no
English collision" claim this run disproves.

## Why deferred

The citations are confirmed and the verdicts re-run. No `reproduce.py` is
committed this round. Several fixes are credible and not mutually
exclusive:

- drop the English homographs from the marker lists;
- derive the `-ung` exemption from "known English stem at the end of the
  token" rather than from "listed prefix + stem";
- give `-heit` the same English-side treatment as `-ung`.

The implementing agent should pick the smallest set that keeps German
recall, which `test_german_ung_nouns_are_still_caught` pins.

## Falsification recipe

```
uv run python -c "import sys; sys.path.insert(0, 'scripts'); import check_card_language as c; print([w for w in ('hamstrung', 'underhung', 'fahrenheit', 'tout', 'nouveau', 'algo', 'nada') if c.flag_text(w)])"
```

If that prints `[]`, the hypothesis is disproved.

Surfaced by: general-purpose audit hunter (repo scripts and CI
workflows), 2026-09-28.
