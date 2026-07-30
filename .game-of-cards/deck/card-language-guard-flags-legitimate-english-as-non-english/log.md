## 2026-07-29T05:54:54Z — Closure

- **What changed**: `scripts/check_card_language.py:129` — the flat
  `SUFFIX_EXCEPTIONS` frozenset is replaced by `ENGLISH_UNG_STEMS` +
  `ENGLISH_UNG_PREFIXES` and the `_is_english_ung_word` predicate, so the English
  side of the `-ung` collision is *derived* rather than enumerated; `des` is
  removed from the French `MARKER_WORDS` block as an English acronym; the layer-2
  comment and module docstring no longer claim the exception set is exhaustive.
- **Verification**: reproduce.py exit 0, was exit 1 with 9/26 English `-ung`
  words and 4/4 English card titles falsely flagged. All 15 German `-ung` nouns
  still caught — the invariant, unchanged on both sides of the fix. Replayed
  against `HEAD:scripts/check_card_language.py`, four of the five new assertions
  fail. Guard reports `English-only: clean (685 cards scanned)`.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is empty). Recording the principle anyway rather than calling this purely
  mechanical: the fix invokes *derive, do not re-enumerate*, the shape this
  deck already carries five open cards against
  (`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
  and siblings). Those cards are about a second in-repo copy of one rule; this
  one is a hand-list standing in for an open morphological family, so it is the
  same principle on a different substrate — which is why it was fixed rather
  than folded into that family as a sixth instance.
- **Project impact**: n/a — repo-local script. Ships to no consumer, has no
  plugin mirror, is not a template; both drift guards
  (`sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check`) green
  with no mirror regeneration.
- **Tests**: 850 passed / 0 failed / 0 xfailed (was 845; five added in
  `tests/test_card_authoring_rules.py::EnglishOnlyUngCollisionTest`, plus four
  entries appended to `PRECISION_CASES`).

### Why the predecessor's validation could not have caught this

`card-authoring-rules-in-agents-md-have-no-enforcement-path` adopted the suffix
thresholds by sweeping "every one of the 4,363 distinct tokens in the deck's
scanned fields: zero matches". That measures *present* false positives, not
reachable ones — the live deck contains no `-ung` participle and no mention of
DES, so the sweep was clean while the predicate stayed wrong for everything the
deck had not yet said. The lesson generalizes past this card: a
precision-first guard validated against current data is validated against the
wrong population. `test_exemption_composes_beyond_the_source_literals` is the
countermeasure — it composes prefix×stem, keeps the forms absent from the
guard's own source text, and requires each to be exempt, so no enumeration can
satisfy it regardless of what the deck happens to contain.

### Surfaced during the fix, filed not fixed

The same predicate has a recall failure in the opposite direction: `_TOKEN_RE`
is `[a-z]+`, so an umlaut separates tokens instead of matching, and the eight
digraph-spelled German marker entries can never fire on natively-spelled input.
Filed as `card-language-guard-misses-german-spelled-with-umlauts` at
`human_gate: none` with its own reproduce and a rubric-derived decision
(fold to digraphs, do not dual-spell the entries — the enumerating fix this
card just argued against). Kept separate: opposite failure direction, different
mechanism, and one pull is one card.

## Closure verification (2026-07-29T05:55:18Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-07-29 — Closure' present

## 2026-07-29T06:02:00Z — Pattern check: connected to a family root

The Stop-hook pattern check flagged this closure as touching a pattern with
broader applicability. It does, and the root card already exists:
`static-source-guards-never-prove-they-can-catch-an-offender`. Deduped and
connected rather than filed.

The connection is not "another instance of a guard with a blind spot" — it is
the counter-example that bounds that card's remedy. `check_card_language.py` is
the one guard in the repo that already satisfies it; the suite docstring names
the card by title and `RECALL_CASES` is the required demonstration. The defect
closed here shipped anyway, because sensitivity testing and false positives are
invisible to each other: a sensitivity case proves the scanner still fires, and
a false positive is the scanner firing. Every recall case passed for the whole
life of the defect.

That root card is open at `human_gate: decision` with two options; its Option B
registers `(scanner, known-offender-sample)` pairs, which is one-sided by
construction. The evidence landed there as a "Sibling property" section arguing
the pair needs a third element — a known-clean near-miss the corpus does not
already contain — with the reciprocal pointer added to this card's scope
boundary. No `advances` edge: the connection is a shared decision, not value
flow into a closed card, matching the precedent set by
`decide-lowers-a-gate-without-surfacing-unclosed-prerequisites`.

Not filed as a fifth umbrella. The deck already carries four undecided ones of
this shape (that root plus `doc-accuracy-guards-are-opt-in-per-claim-…`,
`draft-gating-is-opt-in-per-surface-…`, `query-flag-validation-is-opt-in-per-flag-…`),
and the mechanism question is identical, so one decision settles both. The
missing act is a decision, not another card.
