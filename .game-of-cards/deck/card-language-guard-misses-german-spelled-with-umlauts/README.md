---
title: card-language-guard-misses-german-spelled-with-umlauts
summary: "The English-only card guard tokenizes with `[a-z]+`, so a native umlaut acts as a token separator and shatters the word around it into fragments that match nothing. Eight of the German marker entries encode their umlaut as an ASCII digraph, which makes them unreachable from natively-spelled input, and the suffix layer degrades the same way: the same German phrase is caught in transliteration and missed with its real spelling."
status: done
stage: null
contribution: medium
created: "2026-07-29T05:52:17Z"
closed_at: "2026-07-29T06:12:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every native spelling in the marker and phrase pairs is flagged
  - [x] TDD: each of the eight transliterated German marker entries fires on its natively-spelled form
  - [x] TDD: the three phrase pairs give the same verdict transliterated and natively spelled
  - [x] TDD: a natively-spelled German -ung noun alone is flagged by the suffix layer (folding lifts the token back over MIN_SUFFIX_TOKEN_LEN)
  - [x] TDD: no precision regression — every entry in `PRECISION_CASES` and the whole `ENGLISH_UNG_FAMILY` still read clean
  - [x] MECHANICAL: the docstring's recall disclaimer is narrowed to what it actually covers (cognate-only text), since native spelling is no longer the gap
  - [x] TDD: full suite green (`uv run python -m unittest discover -s tests`) and `uv run goc validate` clean
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
scope. Do not "fix" the summary by pasting the tokens back in. The same
constraint reached `definition_of_done`, which is also scanned: one DoD item
illustrated the suffix-layer case with a natively-spelled German `-ung` noun,
which was invisible while the defect was live and became a real finding on this
card the moment folding worked. It now states the shape instead of spelling a
token — see "Fix (landed)" step 4. Both the diagnosis above and the phrase pairs
below are body text, which stays out of scope by design.)

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

## Fix (landed)

Repo-local only: `scripts/check_card_language.py` ships to no consumer, has no
plugin mirror, and is not a template. Both drift guards agree —
`sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` green
with no mirror regeneration.

1. **Fold before tokenizing**, as decided — one added table, one added method
   call in `flag_text`, and `_TOKEN_RE` plus all 115 German marker entries left
   exactly as they were:

   ```python
   _UMLAUT_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
   ...
       for token in _TOKEN_RE.findall(text.lower().translate(_UMLAUT_FOLD)):
   ```

   Folding after `.lower()` covers `Ä`/`Ö`/`Ü` through the lowercase mapping
   instead of doubling the table.

2. **`tests/test_card_authoring_rules.py` grows `EnglishOnlyNativeSpellingTest`**
   (seven methods) plus one `RECALL_CASES` entry. Per the decision's own
   argument, the new data is a *pairing* — `NATIVE_SPELLING_PAIRS` and
   `GERMAN_PHRASE_PAIRS` assert the two spellings return the identical reason
   list, so neither spelling can be fixed at the other's expense — and one
   method checks the eight transliterated forms really are marker entries, so a
   renamed entry cannot make the pairs vacuous.

3. **The docstring's recall disclaimer now names both gaps it actually has.**
   Cognate-only text was the only one it listed; the accented spellings of the
   other four languages are the second, and folding does not reach them (no
   digraph convention to fold *into* — that needs Unicode NFD plus
   combining-mark strip, a different mechanism). Deliberately left unfixed:
   German is this repo's only real incident. File separately if a non-German
   card ever slips through.

4. **One DoD item on this card was reworded**, for the reason the "Empirical
   evidence" parenthetical gives: it illustrated the suffix-layer case with a
   natively-spelled German `-ung` noun, and `definition_of_done` is a scanned
   field, so the working fix immediately flagged this card. Intent unchanged; the
   token now lives in the test file, which the guard does not read.

### Verification

`reproduce.py` exits 0, was 1 — 8/8 marker entries unreachable from native
spelling and 3/3 phrase pairs caught only in transliteration, now 0/8 and 0/3.
Its token column reads through the fold via `getattr`, so the script still shows
the shattering when replayed against the pre-fix guard. Full suite 857 tests
green (was 850); guard reports `English-only: clean (686 cards scanned)`;
`uv run goc validate` clean with no new warnings.

Replayed against `HEAD:scripts/check_card_language.py`, **all seven** new methods
fail. That number is load-bearing for one of them: pre-fix, both native titles in
the evidence above *were* flagged — one via `berechtigung`, one via `nicht`, each
umlaut-free by accident — so `assertTrue(flag_text(title))` would have passed on
the broken guard. `test_native_title_is_flagged_on_the_umlaut_word_itself` names
the token the finding must cite instead, which is what makes it discriminate.

Precision was the risk the decision flagged, and it holds two ways: the sampled
proof is `PRECISION_CASES` and `ENGLISH_UNG_FAMILY` unchanged and green, and
`test_folding_cannot_change_any_ascii_token` states the property they are drawn
from — English carries no `ä ö ü ß`, so the fold is the identity on every ASCII
token and cannot move a token into or out of a marker class.
