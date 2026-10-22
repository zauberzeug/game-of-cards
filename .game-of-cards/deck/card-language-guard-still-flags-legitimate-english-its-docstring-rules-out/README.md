---
title: card-language-guard-still-flags-legitimate-english-its-docstring-rules-out
summary: "scripts/check_card_language.py documented three precision claims that its behavior broke: no marker word is ever legitimate English, eight of nine German suffixes have no English collision, and no future prefix can make an -ung word a false positive. Seven common English words (listed in the body, not here, because this field is scanned) failed the guard. Fixed: four English homographs left the marker lists, one suffixed word is exempt by exact match, and the -ung exemption splits its stems so the five that end no German noun take any first element. The docstrings now match behavior and name the 47 dictionary words still flagged."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:39:06Z"
closed_at: "2026-10-11T04:56:02Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, test]
definition_of_done: |
  - [x] TDD: a reproduce.py feeds `flag_text` the seven English words quoted in this card's Hypothesis section and asserts none is flagged — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: `tests/test_card_authoring_rules.py` asserts clean verdicts for English words outside the guard's own prefix × stem literals (at least one prefix not in `ENGLISH_UNG_PREFIXES`, one word on a suffix the docstring calls collision-free, one marker-list homograph), so the property the docstrings claim is tested rather than restated
  - [x] MECHANICAL: the docstring claims at `scripts/check_card_language.py:49-50`, `:101-104`, `:147-148` and `:160-162` match the guard's actual behavior; drop the `unverified` tag once reproduce.py lands; append a post-close pointer to `card-language-guard-flags-legitimate-english-as-non-english/log.md`
worker: {who: "claude[bot]", where: main}
---

# The card-language guard still flags legitimate English its docstring rules out

> **Fixed and verified.** `reproduce.py` exits 0; before the fix it exited 1
> with all seven words flagged. An audit hunter filed this card UNVERIFIED on
> 2026-09-28. It was confirmed and fixed on 2026-10-11.

## Location

All four claims were in `scripts/check_card_language.py`. The line numbers
below are from filing time, and the fix rewrote every comment they point at:

- `:101-104`, the `MARKER_WORDS_BY_LANGUAGE` comment: "Every entry is a claim
  that its appearance in a card is a language slip and never legitimate
  English". Yet the French list carried `tout` and `nouveau`, and the Spanish
  or Portuguese list carried `algo` and `nada`. All four are in English use:
  `tout` is a noun and a verb, `nouveau` names the Linux driver for NVIDIA
  GPUs (and *art nouveau*), `algo` is engineering shorthand for "algorithm",
  and `nada` is informal English.
- `:49-50` and `:147-148`: "Eight of the nine [suffixes] have no English
  collision at any length". Yet `-heit` matched *fahrenheit*.
- `:160-162`: "the stem set is closed … and no future prefix combination can
  become a new false positive." The stems were closed, but the prefixes were a
  list of seven (`ENGLISH_UNG_PREFIXES`). Any English word on a listed stem
  with an unlisted prefix was flagged: *hamstrung*, *underhung*.
- `tests/test_card_authoring_rules.py:319-330`
  (`test_exemption_composes_beyond_the_source_literals`) combined only the
  listed prefixes with the listed stems. So it could not see an unlisted
  prefix, which is exactly the gap `:160-162` said could not exist.

## Hypothesis

The guard rejects ordinary English that its own docstrings promise it
accepts. At filing, `flag_text` returned:

```
'retry budget is hamstrung by a fixed cap' -> ["German '-ung' ending on token 'hamstrung'"]
'underhung rotor' -> ["German '-ung' ending on token 'underhung'"]
'convert fahrenheit to celsius' -> ["German '-heit' ending on token 'fahrenheit'"]
'the tout for the new release' -> ["French marker word 'tout'"]
'art nouveau styling in the site' -> ["French marker word 'nouveau'"]
'the algo is fine' -> ["Spanish or Portuguese marker word 'algo'"]
'nada happens' -> ["Spanish or Portuguese marker word 'nada'"]
```

The seven words appear only here in the body, which the guard does not scan.
The first draft of this card named them in its summary and DoD, and the guard
reported 14 findings against it.

The defect is reachable from ordinary authoring. The guard runs as the
`card-language` pre-commit hook and in CI through `test_live_deck_is_clean`,
so a card titled `retry-budget-is-hamstrung-by-a-fixed-cap` failed both.

## Verdict: confirmed, and wider than seven words

`reproduce.py` against the pre-fix guard (HEAD `c644a317`): `English words
still flagged: 7/7`, exit 1.

The seven were a sample. Sweeping hunspell's en_US dictionary (79,013
entries, 128,165 distinct words with its affix rules applied) through the
pre-fix guard found more cases under each of the three claims:

- **The `-ung` side**: `underslung` and `aqualung` were flagged too, both on
  first elements the list lacked.
- **The "collision-free" endings**: `-lich`, `-ieren`, `-schaft`, `-keit` and
  `-isch` all have dictionary hits as well, though every hit is a German
  loanword or a name. Examples are `schlieren`, `gesellschaft` and Heimlich.
- **The marker lists**: they hold dictionary homographs beyond the card's
  four (`doit`, `seine`, `tutti`, `muss`, `para`, `avoir`), plus names a slug
  splits into a marker token: Los Angeles, Las Vegas, the Oder.

The card's second suggested fix, "derive the `-ung` exemption from a known
English stem at the end of the token", fails the recall constraint the card
itself set. Nine of the 14 stems also end German `-ung` nouns:

| Stem | German noun |
|---|---|
| `lung` | Regelung |
| `rung` | Änderung |
| `sung` | Lösung |
| `dung` | Bildung |
| `hung` | Beziehung |
| `stung` | Leistung |
| `flung` | Verzweiflung |
| `slung` | Abwechslung |
| `sprung` | Ursprung |

As a mutant, that rule turns `test_german_ung_nouns_are_still_caught` red.

## Fix (landed)

The card asked for the smallest set of fixes that keeps German recall:

1. **Four homographs left the marker lists**: `tout` and `nouveau` (French),
   `algo` and `nada` (Spanish or Portuguese). This cost no recall, because
   every `RECALL_CASES` entry is still caught by another marker. The comment
   and the layer-1 docstring now state the criterion the list has always
   used: register, not the dictionary. An entry is a word an English
   engineering card has no reason to use. That is why `nada` goes now even
   though the predecessor kept it: the claim it was kept under is the one this
   card disproved.
2. **The `-ung` stems are split.** `TAIL_SAFE_UNG_STEMS` holds `clung`,
   `strung`, `swung`, `wrung` and `young`. They end no German noun, because
   German has no verb stem ending in `cl`, `str`, `sw`, `wr` or `yo`; an
   `-ern` verb keeps its `e`, as in Polsterung. So any token ending in one of
   them is English, and `hamstrung` reads clean without `ham` being listed.
   The other nine stems keep the exact prefix + stem rule.
   `ENGLISH_UNG_PREFIXES` gains `under` and `aqua`, so the list now holds
   every first element hunspell attests on those nine stems.
3. **`-heit`: `ENGLISH_MARKER_SUFFIX_WORDS = {"fahrenheit"}`, matched
   exactly.** It is a name used as a unit, with no family to derive from. It
   cannot be matched as a tail, because German `Unerfahrenheit`
   (inexperience) ends in it.
4. **Docstrings.** All four cited claims are rewritten to match what the
   guard does. A new "Known false positives" section lists the 47 dictionary
   words still flagged, in two groups, along with the rule for admitting one:
   a real card that needs the word.

The guard is repo-local: it ships to no consumer and has no plugin mirror or
template.

## Verification

- `uv run python .game-of-cards/deck/card-language-guard-still-flags-legitimate-english-its-docstring-rules-out/reproduce.py`
  exits 0 with `0/7` English words flagged and `0/15` German nouns missed. It
  exited 1 before the fix. Adding `--dictionary /usr/share/hunspell/en_US.dic`
  re-runs the sweep and prints the 47 remaining hits.
- `tests/test_card_authoring_rules.py` gains the class
  `EnglishOnlyClaimsBeyondTheLiteralsTest` (6 tests), 4 `PRECISION_CASES`, and
  5 German witness nouns. Each test draws its English from outside the guard's
  literals:
  - tail-safe stems combined with first elements that appear nowhere in the
    guard's source;
  - every native-English `-ung` word in the dictionary;
  - `fahrenheit` on the formerly "collision-free" `-heit` ending;
  - the marker-list homographs.

  A structural test also requires every stem that is not tail-safe to have a
  German witness noun that the guard catches. Run against the pre-fix guard,
  the file gives 10 failures and 4 errors.
- Mutation checks. Each of four mutants turns a different assertion red:
  - the naive tail rule fails German recall;
  - removing the tail rule fails the unlisted-first-element test;
  - matching `fahrenheit` as a tail fails on `unerfahrenheit`;
  - dropping `under` fails the dictionary test.
- `uv run python scripts/check_card_language.py --check` reports clean across
  801 cards. `uv run goc validate` is clean. The full suite is green.

## Residuals, deliberately left

- The 47 dictionary words in the docstring's "Known false positives" stay
  flagged. They are names and loanwords. The marker entries among them carry
  the French, Spanish and Portuguese recall, a name has no family to derive
  an exemption from, and listing names has no end. Each one gets admitted
  when a real card needs it.
- A compound on one of the nine colliding stems with an unlisted first
  element is still a false positive by construction. Fixing one means adding
  a single entry to `ENGLISH_UNG_PREFIXES`, and that costs no recall because
  the remainder must still be an exact stem.

## Related

- Post-close evidence on
  [card-language-guard-flags-legitimate-english-as-non-english](../card-language-guard-flags-legitimate-english-as-non-english/)
  (done), which recorded the "eight endings have no English collision" claim
  and the decision to keep `nada`. That card now carries a forward pointer
  here.
- Evidence for
  [static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
  (parked on `decision`). A known-clean near-miss built from the scanner's
  own literals repeats the scanner's blind spot. It has to come from a
  population the scanner does not define.
