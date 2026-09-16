---
title: goc-writes-frontmatter-values-a-standard-yaml-reader-retypes-silently
summary: "The emitter's quote trigger documents itself as the union of two oracles — strict-YAML legality and the vendored parser's coercions — but the strict half only ever checks legality, never type resolution. So every scalar a standard YAML reader resolves to a non-string (floats, signed/underscored/base-prefixed ints, the YAML 1.1 on/off booleans) is emitted bare: a card claimed on git branch 1.5 writes 'where: 1.5' that PyYAML reads as a float, and branch 'off' writes 'where: off' that PyYAML reads as False. 154 of this repo's 762 cards already carry a bare date-only 'created' that a strict reader types as a date while the other 608 stay strings."
status: open
stage: null
contribution: high
created: "2026-09-16T05:38:20Z"
closed_at: null
human_gate: decision
advances:
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question — does the strict-coercion term include YAML's date/timestamp resolvers — is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`.
  - [ ] TDD: `reproduce.py` exits zero. All three checks must flip, not just check A: the emitter sweep, the two end-to-end `goc status ... active` branch claims, and the shipped-deck date count (whose expected value depends on the decision above — 0 under Option B, unchanged and asserted-as-intended under Option A).
  - [ ] TDD: a regression test asserts the *oracle*, not a shape list — for a generated corpus of plain scalars it checks that `_yaml_inline` quotes exactly those a strict resolver retypes, so a resolver family nobody enumerated is covered the moment it is reachable. It must fail on today's tree.
  - [ ] TDD: `tests/test_emitter_strict_yaml_quoting.py` still passes, and the new term is added to the union in `_yaml_inline` (`goc/engine.py:346-363`) rather than folded into `_parser_coerces_scalar` — the two answer different questions and merging them is what hid this term for eight cards.
  - [ ] MECHANICAL: the union comment at `goc/engine.py:346-355` and the "correct oracle" note at `goc/engine.py:218-223` both name three terms, not two, so the next reader cannot re-derive the two-term version. `_DATE_RE`'s exclusion note at `goc/engine.py:289-291` states which of the two oracles it is exempt from.
  - [ ] MECHANICAL: `scripts/check_card_frontmatter_yaml.py` either grows a retyping check or its docstring states that retyping is out of its scope and names this card — the guard currently reads as if it covers strict-reader safety in full.
  - [ ] PROCESS: `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting` is amended with this card's constraint (deriving the trigger from `yaml_lite` alone cannot see any of the 20 shapes) so its parked decision is taken with it in hand.
  - [ ] MECHANICAL: mirrors re-synced (`pre-commit run --all-files`) and the OpenClaw port re-run; `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# goc writes frontmatter values a standard YAML reader retypes silently

The emitter's quote trigger is documented as the union of two oracles. Only one
and a half of them are implemented: the strict-YAML half checks **legality** and
never **type resolution**, so a legal plain scalar that a standard YAML reader
resolves to a float, int or bool is emitted bare. goc's own parser reads it back
as a string and every surface agrees with itself; every reader outside goc gets a
different type for the same field.

## Location

`goc/engine.py:346-363` — the trigger in `_yaml_inline`:

```python
    # The quote trigger is the UNION of two oracles, because either one alone
    # leaves real defects standing. Strict-YAML legality (the first two
    # clauses) covers shapes the vendored parser reads back faithfully but no
    # other YAML reader accepts — `goc install` promises consumers each card is
    # "a plain Markdown file with YAML frontmatter". Parser reinterpretation
    # (the last three) covers shapes that are legal YAML yet come back from
    # `yaml_lite` as a different value, or crash it.
    if (
        _YAML_NEEDS_QUOTE.search(s)
        or _opens_with_yaml_indicator(s)
        or _parser_coerces_scalar(s)
        or bool(_YAML_BLOCK_HEADER_RE.match(s))
        or s != s.strip()
    ):
```

Supporting sites:

| Site | Role |
|---|---|
| `goc/engine.py:214` | `_YAML_NEEDS_QUOTE` — character legality |
| `goc/engine.py:265` | `_opens_with_yaml_indicator` — opening-character legality |
| `goc/engine.py:282` | `_parser_coerces_scalar` — coercion, derived from `yaml_lite`'s recognizers |
| `goc/engine.py:427` | `_emit_worker` — the reachable caller (`worker.where`) |
| `goc/_vendor/yaml_lite.py:43,51-53` | `_INT_RE`, `_NULL_SET`, `_TRUE_SET`, `_FALSE_SET` — the only recognizers the coercion term knows |

## What's broken

Name the three questions the union has to answer about a plain scalar:

1. *Is it legal YAML at all?* — covered, twice over (`_YAML_NEEDS_QUOTE`,
   `_opens_with_yaml_indicator`, `_contains_line_break`, `s != s.strip()`).
2. *Would `yaml_lite` hand it back as a different value?* — covered by
   `_parser_coerces_scalar`, which derives itself from the parser's own
   recognizers precisely so the two cannot drift.
3. *Would a **standard** reader hand it back as a different value?* — **not
   asked anywhere.**

Question 3 is not a restatement of question 2. `yaml_lite` is deliberately
narrower than a YAML 1.1 resolver: it has an int regex and no float regex, its
boolean sets stop at `true/yes/false/no`, and its int regex is the canonical
decimal form only. Every shape in the gap between that and a real resolver —
floats, `+5`, `007`, `0x1F`, `0b101`, `1_000`, and the `on`/`off` boolean pair —
is legal YAML (so questions 1 says "fine") and comes back from `yaml_lite`
unchanged (so question 2 says "fine"), and is therefore written bare.

The engine already knows this is the wrong oracle. The comment at
`goc/engine.py:218-223`, added when the legality half was derived from the spec,
says so in as many words:

> the parser round-trips `!tag`, `%dir`, `- item`, `? key`, `|pipe` and `>fold`
> faithfully while strict YAML refuses all six, so a trigger derived from
> parser behaviour alone stays silent on every one of them. **The correct oracle
> is the union of strict-YAML legality and the parser's coercions**

That sentence names two terms and the code implements exactly those two. The
third — strict-YAML *coercions* — is the one nobody wrote, and it is the only
term that can see this defect.

### Why the family's eight closed cards all missed it

Every prior card in this family used `yaml_lite` as its oracle and closed when
`yaml_lite` agreed with the emitter again:

- `frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values`
  — "re-parsed as int / None / bool", i.e. re-parsed by `yaml_lite`.
- `frontmatter-emitter-writes-float-values-bare-that-parse-back-as-strings` —
  closed as *latent* on the reasoning that `yaml_lite` has no float regex, so a
  bare float "reads back as the string '3.14'". True of `yaml_lite`; the
  opposite of true for every other reader, which is what makes the same bare
  float a defect rather than a non-event.
- `yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values` —
  tightened `_INT_RE` so `007` stops coercing *in `yaml_lite`*, which removed
  `007` from `_parser_coerces_scalar`'s reach and so stopped the emitter
  quoting it.

The two cards that did use a strict reader as the oracle
(`goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse`,
`card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it`) both
asked only whether the reader *refuses*. A reader that quietly succeeds with the
wrong type is the harder half and was never asked about.

The repo-local guard cannot catch it either: `scripts/check_card_frontmatter_yaml.py`
scopes itself in its own docstring to "every card's frontmatter must be
**readable** by a strict YAML parser" and checks three refusal shapes. A retyped
value is perfectly readable.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-writes-frontmatter-values-a-standard-yaml-reader-retypes-silently/reproduce.py`
(exit 1):

```
A. emitter sweep — scalars emitted bare that a strict reader retypes
   '1.5'      emitted as 1.5        -> PyYAML reads 1.5 (float)
   '-2.0'     emitted as -2.0       -> PyYAML reads -2.0 (float)
   '+3.5'     emitted as +3.5       -> PyYAML reads 3.5 (float)
   '1.0e-5'   emitted as 1.0e-5     -> PyYAML reads 1e-05 (float)
   '.5'       emitted as .5         -> PyYAML reads 0.5 (float)
   '.inf'     emitted as .inf       -> PyYAML reads inf (float)
   '-.inf'    emitted as -.inf      -> PyYAML reads -inf (float)
   '.nan'     emitted as .nan       -> PyYAML reads nan (float)
   '.INF'     emitted as .INF       -> PyYAML reads inf (float)
   '+5'       emitted as +5         -> PyYAML reads 5 (int)
   '007'      emitted as 007        -> PyYAML reads 7 (int)
   '0x1F'     emitted as 0x1F       -> PyYAML reads 31 (int)
   '0b101'    emitted as 0b101      -> PyYAML reads 5 (int)
   '1_000'    emitted as 1_000      -> PyYAML reads 1000 (int)
   'on'       emitted as on         -> PyYAML reads True (bool)
   'off'      emitted as off        -> PyYAML reads False (bool)
   'On'       emitted as On         -> PyYAML reads True (bool)
   'Off'      emitted as Off        -> PyYAML reads False (bool)
   'ON'       emitted as ON         -> PyYAML reads True (bool)
   'OFF'      emitted as OFF        -> PyYAML reads False (bool)
   20 of 20 probe shapes retyped

B. reachability — `goc status <card> active` on a named git branch
   branch '1.5': goc wrote  worker: {who: probe-worker, where: 1.5}
                 yaml_lite  {'who': 'probe-worker', 'where': '1.5'}
                 PyYAML     {'who': 'probe-worker', 'where': 1.5}
   branch 'off': goc wrote  worker: {who: probe-worker, where: off}
                 yaml_lite  {'who': 'probe-worker', 'where': 'off'}
                 PyYAML     {'who': 'probe-worker', 'where': False}

C. shipped deck — cards whose date fields a strict reader retypes
   154 card(s) carry a bare date-only created/closed_at (strict reader: date)
   608 card(s) carry the emitter's current quoted form (strict reader: str)

FAIL: 4 check(s) show the strict-reader coercion term is missing.
```

`reproduce.py` re-execs itself under an interpreter that carries PyYAML. PyYAML
is absent from goc's runtime *and* from the project venv by design
(`drop-third-party-runtime-dependencies-from-goc`) — which is the same reason
the engine cannot settle this question by asking a real parser at emit time, and
why the missing term has to be written by hand.

## Why it matters

**Reachability is the CLI, not a hand edit.** Check B does no hand-editing: it
creates a branch, commits, and runs `goc status <title> active`. The engine's
`_auto_populate_worker` (`goc/engine.py:5858`) reads
`git rev-parse --abbrev-ref HEAD` and stores it as `worker.where`, which
`_emit_worker` (`goc/engine.py:427`) interpolates into a flow mapping through
`_yaml_inline`. `1.5` is an ordinary version-branch name and `off` is an
ordinary git ref; neither is rejected anywhere. This is the same reachability
path the closed sibling
`frontmatter-emitter-does-not-quote-integer-looking-string-scalars` established
for this field, one resolver family over.

**The damage is silent and type-shaped, which is worse than a crash.** A
consumer reading `worker.where` gets the float `1.5` where goc stored `"1.5"`,
so a `.startswith("release/")` raises `AttributeError` at a distance; on branch
`off` the value is `False`, so a `if where:` guard takes the "no branch
recorded" path for a card that records one. Nothing warns, and goc's own
surfaces keep showing the right answer, so the divergence is invisible from
inside the tool.

**Check C is present tense, not hypothetical.** 154 of this repo's 762 shipped
cards carry a bare date-only `created` / `closed_at`; a strict reader types
those as `datetime.date` and the other 608 as `str` — the same field, two types,
in one deck, today. Anyone writing the "read the deck with your own YAML
library" integration that
`integrate-github-issues-discussions-and-pull-requests` implies hits this on the
first card.

**The open root card's proposed fix would not close it.**
`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
is parked on "a factoring that derives the emitter's quote decision **from
parser behaviour** (one source of truth)". Deriving from `yaml_lite` is exactly
what cannot see any of the 20 shapes above — `yaml_lite` returns every one of
them as a string. This card is the evidence that the parked decision needs a
third source of truth, not one; it is filed as `advances` that card so the
decision is taken with this constraint in hand.

## Decision required

The non-date half is determined: quote any scalar a standard YAML reader
resolves to a non-string. The date/timestamp resolver is the open question,
because it is the only one whose answer rewrites existing cards.

**The question: does the strict-coercion term include YAML's date and timestamp
resolvers?**

- **Option A — exempt dates.** Treat `created: 2026-05-10` typing as
  `datetime.date` as correct YAML for a date-valued field, and scope the new
  term to float / int / bool. Nothing in the deck is rewritten. Cost: the same
  field keeps two strict-reader types across the deck (154 `date`, 608 `str`),
  and a consumer must handle both.
- **Option B — include dates.** Quote date-shaped scalars too, so every
  frontmatter value is a string under every reader. The 154 legacy cards
  converge to the emitter's current quoted form the next time any verb re-emits
  them — a touch-by-touch migration, not a mass rewrite, with `goc migrate` /
  `goc migrate-list-style` as the precedent for forcing it deck-wide. Cost: a
  diff on 154 cards, and `_DATE_RE`'s "intentionally excluded" note at
  `goc/engine.py:289-291` has to be rewritten rather than extended.

Related but **not** part of this question: whether the three-term union should
be replaced by a single derived oracle at all. That is the root card's
decision; this one only establishes that the third term exists and must be in
whatever shape is chosen.
