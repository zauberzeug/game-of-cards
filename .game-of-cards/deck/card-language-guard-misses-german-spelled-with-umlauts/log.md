## 2026-07-29T06:11:06Z — Closure

- **What changed**: `scripts/check_card_language.py:165` — `_UMLAUT_FOLD`
  (`ä→ae ö→oe ü→ue ß→ss`) is applied after `.lower()` and before
  `_TOKEN_RE.findall`, so an umlaut no longer acts as a token separator that
  shatters the word around it. `_TOKEN_RE` and all 115 German marker entries are
  untouched — folding makes the existing digraph data correct for native input
  rather than rewriting it. The module docstring's recall disclaimer now names
  both gaps it actually has (cognate-only text, and the accented spellings of the
  other four languages, which folding cannot reach).
- **Verification**: reproduce.py exit 0, was exit 1 with 8/8 marker entries
  unreachable from native spelling and 3/3 phrase pairs caught only in
  transliteration — now 0/8 and 0/3. Replayed against
  `HEAD:scripts/check_card_language.py`, all seven new test methods fail. Guard
  reports `English-only: clean (686 cards scanned)`; `uv run goc validate` clean
  with no new warnings; both drift guards (`sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`) green with no mirror regeneration.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is comment-only). Recording the principle anyway rather than calling this
  mechanical: the decision the card carried is *derive, do not re-enumerate*,
  the same principle its sibling
  `card-language-guard-flags-legitimate-english-as-non-english` closed on hours
  earlier. The enumerating alternative here was to widen `_TOKEN_RE` and give
  each umlaut marker entry a second, natively-spelled twin; folding the *input*
  to the spelling the data already uses converges instead, because it needs no
  per-entry maintenance and no future entry can be half-registered.
- **Project impact**: n/a — repo-local script. Ships to no consumer, has no
  plugin mirror, is not a template.
- **Tests**: 857 passed / 0 failed / 0 xfailed (was 850; seven methods added in
  `tests/test_card_authoring_rules.py::EnglishOnlyNativeSpellingTest`, plus one
  entry in `RECALL_CASES`).

### The working fix made this card fail its own guard

`definition_of_done` is a scanned field, and one DoD item illustrated the
suffix-layer criterion with a natively-spelled German `-ung` noun. That token was
invisible for as long as the defect was live — the tokenizer shattered it — so it
passed `--check` when the card was filed, and became a live finding on this very
card the instant folding started working. The item now states the shape and the
token lives in the test file, which the guard does not read.

The card's author had already hit the same wall one field over: the body carries a
note explaining that the `summary` paraphrases rather than quoting the eight
marker entries, because summaries are in scope. So the trap is not specific to
one field — a card *about* a detector, filed at the detector's current
sensitivity, is calibrated against the broken behaviour. Anything the pending fix
will newly detect has to leave the scanned fields before that fix lands. Body
text is the escape hatch, which is exactly why the docstring puts bodies out of
scope.

### Sensitivity assertions have to name the token, not just the verdict

Both native-spelling titles in the card's evidence table were *already* flagged
before the fix — `prüfung-der-berechtigung-schlägt-fehl` via `berechtigung`,
`löschen-entfernt-die-einträge-nicht` via `nicht`, each umlaut-free by accident.
An `assertTrue(flag_text(title))` recall case would therefore have passed against
the broken guard, which is the same shape of false comfort the sibling card
recorded: every `RECALL_CASES` entry passed for the whole life of *its* defect
too. `test_native_title_is_flagged_on_the_umlaut_word_itself` asserts which token
the finding cites, and `test_phrase_pairs_get_the_same_verdict_either_way`
asserts two spellings return the *identical* reason list. Both discriminate;
"is it flagged" does not. This is evidence for the open root card
`static-source-guards-never-prove-they-can-catch-an-offender`, whose Option B
registers `(scanner, known-offender-sample)` pairs — a sample proves nothing
unless the assertion over it can fail for the right reason.

## Closure verification (2026-07-29T06:12:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-07-29 — Closure' present
