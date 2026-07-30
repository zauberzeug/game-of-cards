---
title: card-language-guard-flags-legitimate-english-as-non-english
summary: "The repo-local English-only card guard falsely rejects legitimate English: its hand-enumerated SUFFIX_EXCEPTIONS set covers five `-ung` words but misses nine more from the same open-ended prefix+participle family (sprung, strung, overhung, unslung, ...), and the French marker list contains `des`, which is the English acronym DES. The docstring claims the exception set is exhaustive; it was only ever measured against the tokens the live deck happened to contain, so any future English card using one of these words fails pre-commit and CI."
status: done
stage: null
contribution: medium
created: "2026-07-29T05:43:27Z"
closed_at: "2026-07-29T05:55:22Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — no English case flagged, no German case missed
  - [x] TDD: every one of the 26 English `-ung` words in the probe reads clean, and the 15 German `-ung` nouns still fail the guard
  - [x] TDD: `des` no longer flags, and the French recall case still fails the guard without it
  - [x] TDD: the English `-ung` rule is derived from a closed stem set plus prefixes, asserted on a prefixed form absent from any hand-written list
  - [x] MECHANICAL: the `SUFFIX_EXCEPTIONS` exhaustiveness claim and the docstring homograph list are corrected to match the derived rule
  - [x] TDD: full suite green (`uv run python -m unittest discover -s tests`) and `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# card-language-guard-flags-legitimate-english-as-non-english

The English-only card guard rejects English words as non-English at two
independent sites, so a legitimate card can be blocked at pre-commit and turn
CI red with a language violation it does not have.

## Location

Line numbers and symbols as they stood at filing time — `SUFFIX_EXCEPTIONS` and
the `des` entry no longer exist post-fix. See "Fix (landed)" for what replaced
them.

- `scripts/check_card_language.py:129` — `SUFFIX_EXCEPTIONS`
- `scripts/check_card_language.py:124` — `MARKER_SUFFIXES` / `MIN_SUFFIX_TOKEN_LEN`
- `scripts/check_card_language.py:104` — `des` in the French `MARKER_WORDS` block
- `scripts/check_card_language.py:135` — `flag_text`, the consuming predicate

## What's broken

### Site 1 — the suffix exception set enumerates an open family

The suffix layer flags any token of six or more characters ending in a German
derivational ending, minus a hand-listed exception set:

```python
MARKER_SUFFIXES = ("ungen", "ierung", "ung", "keit", "heit", "schaft", "lich", "isch", "ieren")
MIN_SUFFIX_TOKEN_LEN = 6

# The English words long enough to clear the length floor and still end in a
# marker suffix. All of them are `-ung`; the other eight endings have no English
# collision at any length.
SUFFIX_EXCEPTIONS = frozenset({"unsung", "unsprung", "unstrung", "restrung", "highstrung"})
```

That comment is an exhaustiveness claim — "**The** English words long enough to
clear the length floor" — and it is false. English `-ung` words are not a list;
they are a *family*: a strong-verb participle stem (`hung`, `rung`, `sung`,
`clung`, `flung`, `slung`, `stung`, `swung`, `wrung`, `strung`, `sprung`) plus
the adjective `young`, each optionally carrying a prefix (`un-`, `re-`,
`over-`, `out-`, `up-`, `high-`). The set captured four prefixed forms and one
bare stem, and missed **nine** other members — including `sprung` and `strung`,
the very stems that `unsprung`, `unstrung`, `restrung` and `highstrung` are
built from.

Enumerating members of an open morphological family cannot converge. The next
prefix or stem anybody writes is another false positive.

### Site 2 — `des` is an English acronym in the French marker list

```python
    "French": """
        les des une dans avec mais tout tous toute toutes cette ces sont etre
```

`DES` is the Data Encryption Standard (and `3DES`); it lowercases to `des` and
`flag_text` tokenizes case-insensitively. The module's own contract forbids
exactly this:

```python
# Words common in another European language that are NOT English words, English
# acronyms, or technical tokens. Every entry is a claim that its appearance in a
# card is a language slip and never legitimate English — homographs belong in
# the docstring's exclusion list, not here.
```

`des` is an English acronym, so by the file's own rule it does not belong in
`MARKER_WORDS`. It is also redundant for recall: the French recall case in
`tests/test_card_authoring_rules.py` is caught by `une` and `erreur`, not `des`.

### Why the original validation could not see either one

The closed predecessor [card-authoring-rules-in-agents-md-have-no-enforcement-path](../card-authoring-rules-in-agents-md-have-no-enforcement-path/)
records how the thresholds were adopted:

> The nine `MARKER_SUFFIXES`/`MIN_SUFFIX_TOKEN_LEN` combinations were checked
> against every one of the 4,363 distinct tokens in the deck's scanned fields
> before being adopted: zero matches.

Measuring against the deck as it stood is a check for *present* false
positives, not for the *reachable* ones. The live deck happens to contain no
`-ung` participle and no mention of DES, so a sweep over its tokens returns
clean while the predicate stays wrong for everything the deck does not yet say.
That is why the gap survived the card that introduced the guard: the validation
method and the failure mode are orthogonal.

## Empirical evidence

`uv run python .game-of-cards/deck/card-language-guard-flags-legitimate-english-as-non-english/reproduce.py`
(exit 1 before the fix):

```
SUFFIX_EXCEPTIONS      = ['highstrung', 'restrung', 'unsprung', 'unstrung', 'unsung']
MIN_SUFFIX_TOKEN_LEN   = 6
'des' in MARKER_WORDS  = True

English -ung words falsely flagged: 9/26
  'sprung': German '-ung' ending on token 'sprung'
  'strung': German '-ung' ending on token 'strung'
  'unhung': German '-ung' ending on token 'unhung'
  'unslung': German '-ung' ending on token 'unslung'
  'resprung': German '-ung' ending on token 'resprung'
  'overhung': German '-ung' ending on token 'overhung'
  'overstrung': German '-ung' ending on token 'overstrung'
  'outflung': German '-ung' ending on token 'outflung'
  'upswung': German '-ung' ending on token 'upswung'

English card titles falsely flagged: 4/4
  retry-loop-has-sprung-a-leak: German '-ung' ending on token 'sprung'
  requests-are-strung-together-without-a-budget: German '-ung' ending on token 'strung'
  des-cipher-fallback-is-still-enabled: French marker word 'des'
  triple-des-key-rotation-is-skipped: French marker word 'des'

German -ung nouns no longer caught (recall regression): 0

guard accepts every English case: False
guard still rejects every German case: True
```

The last line is the constraint on the fix: all 15 German `-ung` nouns in the
probe are still caught today, so "raise the floor" and "drop the suffix layer"
are both wrong — the layer earns its keep, only its exception rule is broken.

## Why it matters

The guard runs at two enforcement points, and a false positive is blocking at
both:

1. **`.pre-commit-config.yaml`, hook `card-language`** — `--check`, so exit 1
   aborts the commit. `engine._git_auto_commit` shells out to `git commit`
   without `--no-verify`, so this fires inside `goc new --commit` and inside
   every skill-driven auto-commit. An agent filing a card titled
   `requests-are-strung-together-without-a-budget` gets its commit rejected
   with `German '-ung' ending on token 'strung'`.
2. **`tests/test_card_authoring_rules.py::test_live_deck_is_clean`** — CI on
   every push. A card that reaches `main` by any path that skips pre-commit
   turns the build red, and `test_live_deck_is_actually_being_scanned` makes it
   un-silenceable.

The failure mode is worse than the block itself. The message names a *German*
ending on an English word, so the reader's first move is to re-read a correct
title looking for a language slip that is not there. The documented escape
hatch is to edit `SUFFIX_EXCEPTIONS` — which repeats the same
enumerate-an-open-family mistake one word at a time, and pushes the next
occurrence onto the next author.

Precision is the whole design premise. The docstring trades recall away for it
("a non-English title built entirely from cognates … can still slip through"),
so a false positive is not a tuning nit — it is a failure of the one property
the guard was built to have.

## Fix (landed)

Repo-local only: `scripts/check_card_language.py` ships to no consumer, has no
plugin mirror, and is not a template. Both drift guards confirm it —
`sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` are
green with no mirror regeneration.

1. **Derived the English `-ung` rule instead of enumerating it.** The flat
   `SUFFIX_EXCEPTIONS` frozenset is gone, replaced by a closed stem set, a
   prefix list, and `_is_english_ung_word`, which accepts `stem` or
   `prefix + stem`:

   ```python
   ENGLISH_UNG_STEMS = frozenset({
       "hung", "rung", "sung", "dung", "lung", "clung", "flung", "slung",
       "stung", "strung", "sprung", "swung", "wrung", "young",
   })
   ENGLISH_UNG_PREFIXES = ("un", "re", "over", "out", "up", "down", "high")
   ```

   The stem set is closed in a way the word list is not — English has no
   productive `-ung` suffix, so no new stem can appear — which is what makes
   deriving correct here rather than just longer. Requiring the remainder to be
   an *exact* stem keeps German recall: `Regelung` → `re` + `gelung`, and
   `gelung` is not a stem, so it still fires (verified for all 15 nouns in
   `reproduce.py`).

2. **Dropped `des` from the French `MARKER_WORDS` block**, and added it to the
   docstring's homograph exclusion list, which exists so "the next reader does
   not helpfully add them back."

3. **Corrected the exhaustiveness claim** in the layer-2 comment and the module
   docstring. Both now say eight endings have no English collision and the
   ninth, `-ung`, is exempted by derivation — rather than asserting a
   hand-checked word list is complete.

### Verification

`reproduce.py` exits 0 (was 1: `guard accepts every English case: False`).
`tests/test_card_authoring_rules.py` grows a fifth class,
`EnglishOnlyUngCollisionTest`, plus four entries in `PRECISION_CASES` — 850
tests total, green. Replayed against `HEAD:scripts/check_card_language.py`, four
of the five new assertions fail (9/26 family words flagged, `des` present, no
`ENGLISH_UNG_PREFIXES`, 4/4 phrases flagged); `test_german_ung_nouns_are_still_caught`
passes on both sides, which is the point — it is the invariant, not the fix.

`test_exemption_composes_beyond_the_source_literals` is the assertion that
pins *derivation* rather than a longer list: it composes every prefix with every
stem, keeps the forms that appear nowhere in the guard's source text, and
requires each to be exempt. No enumeration can satisfy it. Three of the German
recall nouns (`Regelung`, `Rechnung`, `Reinigung`) begin with the `re-` prefix,
so they hold the exact-stem requirement in place against a `startswith`
regression.

The guard itself reports `English-only: clean (685 cards scanned)`, and
`uv run goc validate` is clean across the deck.

Two further homographs were considered and **deliberately kept**, so the next
reader does not have to re-derive the call: `nada` (a dictionary English noun,
but marked informal — the Spanish reading dominates in a card) and `les` (the
CFD acronym LES, far weaker than DES as a technical token and load-bearing for
the Spanish/French recall cases). Both are recorded here rather than removed;
revisit only with a real false positive.

Connected, not re-filed: this closure is an instance of
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
§ "Sibling property: sensitivity is necessary but not sufficient" — and the
counter-example that bounds it. `tests/test_card_authoring_rules.py` already
complies with that root card (its docstring names it, and `RECALL_CASES` is the
demonstration), yet every recall case passed throughout this defect's life. A
sensitivity case proves the scanner still fires; a false positive *is* the
scanner firing, so the two directions are invisible to each other's test. That
root's pending mechanism decision is the same decision this property needs — its
Option B registration pair wants a third element, a known-clean near-miss — so
the evidence went there rather than into a fifth undecided umbrella card.

Not in scope, and filed separately as
[card-language-guard-misses-german-spelled-with-umlauts](../card-language-guard-misses-german-spelled-with-umlauts/):
the guard's umlaut blind spot. `_TOKEN_RE` is `[a-z]+`, so an umlaut separates
tokens rather than matching, and the eight digraph-spelled German markers can
never fire on natively-spelled input. That is the *recall* side of the same
predicate — the opposite failure direction from this card — so it gets its own
reproduce and its own fix rather than riding along here.
