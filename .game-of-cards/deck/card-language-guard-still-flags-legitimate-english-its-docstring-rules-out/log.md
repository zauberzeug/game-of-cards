## 2026-10-11T04:55:41Z — Closure

- **What changed**: `scripts/check_card_language.py`:
  - `algo`, `nada`, `tout` and `nouveau` left `MARKER_WORDS_BY_LANGUAGE`.
  - New `ENGLISH_MARKER_SUFFIX_WORDS` exempts `fahrenheit` by exact match.
  - New `TAIL_SAFE_UNG_STEMS` (`clung`, `strung`, `swung`, `wrung`, `young`):
    any token ending in one is English. The other nine `-ung` stems keep the
    exact prefix + stem rule, and `ENGLISH_UNG_PREFIXES` gains `under` and
    `aqua`.
  - The four cited docstring claims are rewritten to match the code. A new
    "Known false positives" section lists the 47 hunspell en_US words the
    guard still flags.
- **Verification**:
  - `reproduce.py` exits 0 with `0/7` English words flagged and `0/15` German
    nouns missed. Against HEAD `c644a317` it gave 7/7 and exit 1.
  - Against the pre-fix guard, the new tests give 10 failures and 4 errors.
  - Each of four mutants is caught by a different assertion: the naive tail
    rule (the card's second suggested fix), the tail rule removed,
    `fahrenheit` matched as a tail, and `under` dropped.
  - The guard reports clean across 801 cards. `goc validate` is clean, and
    `sync_plugin_assets.py --check` is green with no mirror regenerated: the
    script is repo-local.
- **Audit**: no rubric configured; mechanical fix. The predecessor's principle
  still holds and was applied on both sides: derive where a family exists (the
  `-ung` stems), and match exactly only where none does (`fahrenheit`, a name
  used as a unit).
- **Project impact**: n/a. The guard is repo-local and ships to no consumer.
- **Tests**: 1297 passed / 0 failed / 0 xfailed. Six tests were added in
  `EnglishOnlyClaimsBeyondTheLiteralsTest`, plus 4 `PRECISION_CASES` entries
  and 5 `GERMAN_UNG_NOUNS` witnesses.

### Choosing among the card's three suggested fixes

The card listed three fixes and asked for the smallest set that keeps German
recall. All seven words had to read clean, so each of the three claims needed
some change. What had to be chosen was the mechanism for each:

- The literal second suggestion ("known English stem at the end of the token")
  costs recall. `Regelung`, `Änderung`, `Lösung` and six more German nouns end
  in an English stem. So only stems that end no German noun can be tails.
- A smaller alternative was to add `ham` and `under` to the prefix list. It
  would clear the seven words, but it fails DoD item 2: no word on a prefix
  outside the list could read clean, so the docstring property would still be
  restated rather than tested.

### Surfaced, documented, not filed

The dictionary sweep found 47 words still flagged: names and loanwords, among
them Los Angeles, Samsung and `schlieren`. They are recorded in the guard's
docstring together with the rule for admitting one, which is a real card that
needs the word. This repeats the predecessor's "revisit only with a real
false positive". It is a policy, so a speculative card would add noise.

### Connected

The parked root
`static-source-guards-never-prove-they-can-catch-an-offender` gained a
constraint on its proposed known-clean element: the sample must not be
generated from the scanner's own literals. Evidence only; its gate is
unchanged. The predecessor carries a forward pointer here in its README and
`log.md`.

## Closure verification (2026-10-11T04:55:58Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-11 — Closure' present
