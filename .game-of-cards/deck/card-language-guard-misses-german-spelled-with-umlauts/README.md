---
title: card-language-guard-misses-german-spelled-with-umlauts
summary: "The English-only card guard tokenizes with `[a-z]+`, so a native umlaut acts as a token separator and shatters the word around it into fragments that match nothing. Eight of the German marker entries encode their umlaut as an ASCII digraph, which makes them unreachable from natively-spelled input, and the suffix layer degrades the same way: the same German phrase is caught in transliteration and missed with its real spelling."
status: active
stage: null
contribution: medium
created: "2026-07-29T05:52:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — every native spelling in the marker and phrase pairs is flagged
  - [ ] TDD: each of the eight transliterated German marker entries fires on its natively-spelled form
  - [ ] TDD: the three phrase pairs give the same verdict transliterated and natively spelled
  - [ ] TDD: `Prüfung` alone is flagged by the suffix layer (the token survives folding at >= MIN_SUFFIX_TOKEN_LEN)
  - [ ] TDD: no precision regression — every entry in `PRECISION_CASES` and the whole `ENGLISH_UNG_FAMILY` still read clean
  - [ ] MECHANICAL: the docstring's recall disclaimer is narrowed to what it actually covers (cognate-only text), since native spelling is no longer the gap
  - [ ] TDD: full suite green (`uv run python -m unittest discover -s tests`) and `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# card-language-guard-misses-german-spelled-with-umlauts

The English-only card guard's tokenizer drops non-ASCII letters, so the umlaut
half of its German marker list is dead code: it can only match German that was
typed in ASCII transliteration, which is not how German is written.

## Location

- `scripts/check_card_language.py:165` — `_TOKEN_RE = re.compile(r"[a-z]+")`
- `scripts/check_card_language.py:173` — the `for token in _TOKEN_RE.findall(text.lower())`
  loop in `flag_text` (defined at `:168`)
- `scripts/check_card_language.py:85` — the German `MARKER_WORDS_BY_LANGUAGE`
  block, whose entries spell the umlaut as an ASCII digraph

## What's broken

`flag_text` lowercases the field and then splits it on anything outside `[a-z]`:

```python
_TOKEN_RE = re.compile(r"[a-z]+")
...
    for token in _TOKEN_RE.findall(text.lower()):
```

`ü`, `ö`, `ä` and `ß` are outside that class, so an umlaut does not merely fail
to match — it acts as a **token separator**, shattering the word around it.
`prüfen` yields `['pr', 'fen']`; `können` yields `['k', 'nnen']`; `über` yields
`['ber']`. None of those fragments is a marker word, and most are below
`MIN_SUFFIX_TOKEN_LEN`, so both detection layers go quiet.

Meanwhile the German marker block spells exactly those words in ASCII
transliteration:

```
        haben hatte hatten kann koennen muss muessen soll sollen sollte darf
        duerfen sich seine ihre unser unsere jeder jede jedes alle alles etwas
        ...
        funktioniert ueber unter aendern loeschen erstellen anzeigen pruefen
```

Eight entries — `ueber`, `koennen`, `muessen`, `duerfen`, `aendern`,
`loeschen`, `pruefen`, `moeglich` — encode an umlaut as a digraph. A token
containing `ue` can only arrive from text that was *already* transliterated, so
those eight entries are unreachable from the input the guard will actually see.
The other 107 German entries are unaffected because they carry no umlaut.

The suffix layer degrades the same way, and it is the layer that matters most
for titles (slugs drop function words, which is the whole reason the layer
exists). `Prüfung` → `pr` + `fung`; `fung` is four characters, under the
six-character floor, so the `-ung` ending never gets tested.

## Empirical evidence

`uv run python .game-of-cards/deck/card-language-guard-misses-german-spelled-with-umlauts/reproduce.py`
(exit 1):

```
tokenizer = '[a-z]+', MIN_SUFFIX_TOKEN_LEN = 6

marker entry native     tokens from native       flagged?
ueber        über       ['ber']                  False
koennen      können     ['k', 'nnen']            False
muessen      müssen     ['m', 'ssen']            False
duerfen      dürfen     ['d', 'rfen']            False
aendern      ändern     ['ndern']                False
loeschen     löschen    ['l', 'schen']           False
pruefen      prüfen     ['pr', 'fen']            False
moeglich     möglich    ['m', 'glich']           False

marker entries unreachable from native spelling: 8/8
  ['ueber', 'koennen', 'muessen', 'duerfen', 'aendern', 'loeschen', 'pruefen', 'moeglich']

same text, transliterated vs. natively spelled:
  'pruefung schlaegt fehl'   -> True
  'prüfung schlägt fehl'     -> False
  'loeschen der eintraege'   -> True
  'löschen der einträge'     -> False
  'ueber die groesse'        -> True
  'über die größe'           -> False

phrases caught only in transliteration: 3/3

native-spelling card titles:
  'prüfung-der-berechtigung-schlägt-fehl' -> ["German '-ung' ending on token 'berechtigung'"]
  'löschen-entfernt-die-einträge-nicht' -> ["German marker word 'nicht'"]

native German is caught: False
```

The phrase pairs are the cleanest statement of the defect: the *same German
text* is caught in transliteration and missed with its real spelling.

(This card's `summary` deliberately paraphrases instead of quoting the eight
entries. Summaries are in scope for the guard, so naming them there fails
`--check` on this very card — the reason the docstring puts card bodies out of
scope. Do not "fix" the summary by pasting the tokens back in.)

Read the last block carefully — it is why this is a recall gap and not a total
blind spot. Both native titles *are* flagged, but neither is flagged on the word
carrying the umlaut. `prüfung-der-berechtigung-schlägt-fehl` is caught only
because `berechtigung` happens to be umlaut-free, and
`löschen-entfernt-die-einträge-nicht` only because of `nicht`. Recall on native
German therefore rests entirely on whichever ASCII words happen to co-occur —
it is luck, not detection.

## Why it matters

This is the *precision-first* guard's other half. The sibling card
[card-language-guard-flags-legitimate-english-as-non-english](../card-language-guard-flags-legitimate-english-as-non-english/)
fixed two false positives; this one is the false negative, and it hits the
likeliest real offender rather than a hypothetical.

The historical offender the guard was built for,
`openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session`, was umlaut-free
by luck. A German author writing `prüfung-schlägt-fehl` or
`löschen-räumt-nicht-auf` is writing what their keyboard produces; the
transliterated digraph spelling is a workaround people use when a system cannot
take umlauts, and the guard silently assumes it.

The scope is bounded and worth stating: the marker layer keeps most of its
German recall through the 107 umlaut-free entries, and `summary` /
`definition_of_done` are prose likely to contain one of them. The real exposure
is short slug titles, which is the case the suffix layer was added to cover and
the case where a single shattered token is the whole signal.

## Decision (rubric-derived)

**Fold umlauts and `ß` into their ASCII digraphs before tokenizing** — add a
normalization step in `flag_text` ahead of `_TOKEN_RE.findall`, mapping
`ä→ae ö→oe ü→ue ß→ss`, and leave `_TOKEN_RE` and every marker entry as they are.

The alternative is to widen `_TOKEN_RE` to `[a-zäöüß]+` and add the native
spelling of all eight entries alongside the transliterated one. That is the
enumerating fix, and this repo just closed a card against exactly that shape:
[card-language-guard-flags-legitimate-english-as-non-english](../card-language-guard-flags-legitimate-english-as-non-english/)
replaced a hand-listed exception set with a derived rule because enumerating
members of an open family cannot converge. Dual-spelling entries would put the
same trap back in the marker layer — every future umlaut entry would need both
forms, and the one somebody forgets is a silent miss.

Folding also repairs the suffix layer for free, which widening does not:
`Prüfung` → `pruefung` is eight characters and matches `-ung`, whereas
`[a-zäöüß]+` yields `prüfung`, whose `endswith("ung")` test passes but whose
length and stem checks now run over a mixed-alphabet token. And the marker list
is *already written* in digraph form, so folding is the change that makes the
existing data correct rather than rewriting it.

Precision risk is the thing to test, not assume: folding creates `ue`/`oe`/`ae`
digraphs in tokens that did not have them, so the DoD requires the full
`PRECISION_CASES` list and `ENGLISH_UNG_FAMILY` to stay clean. English text has
no `ä/ö/ü/ß`, so no English token can change under folding — but that is an
argument for the assertion, not a substitute for it.

## Fix

1. In `flag_text`, fold before tokenizing:

   ```python
   _UMLAUT_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
   ...
       for token in _TOKEN_RE.findall(text.lower().translate(_UMLAUT_FOLD)):
   ```

   Fold after `.lower()` so `Ä` is covered by the lowercase mapping rather than
   needing its own entry.

2. Extend `tests/test_card_authoring_rules.py`: a native-spelling recall case
   per affected marker entry, the three phrase pairs asserted equal, and
   `Prüfung` on the suffix layer alone. `PRECISION_CASES` and
   `ENGLISH_UNG_FAMILY` are the no-regression side.

3. Narrow the module docstring's recall disclaimer. It currently reads "a
   non-English title built entirely from cognates … can still slip through",
   which does not cover native spelling; once folding lands, cognates really are
   the remaining gap and the sentence becomes true as written.

Out of scope: the other four languages carry accented characters too (`é`, `à`,
`ñ`, `ç`, `ì`), and their marker entries are spelled unaccented (`despues`,
`porque`, `perche`). Folding does not reach those — there is no digraph
convention to fold *into*, so the entries would have to be matched
accent-insensitively (Unicode NFD plus combining-mark strip), which is a
different mechanism. File separately if a non-German card ever slips through;
German is this repo's actual exposure and the only language with a real
incident.
