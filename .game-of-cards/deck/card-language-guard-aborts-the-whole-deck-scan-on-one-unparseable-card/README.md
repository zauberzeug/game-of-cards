---
title: card-language-guard-aborts-the-whole-deck-scan-on-one-unparseable-card
summary: "`scripts/check_card_language.scan_card` calls `parse_frontmatter` with no `FrontmatterError` net, so one card with an unterminated `---`, a missing space after a colon, or a duplicate mapping key aborts the entire English-only scan with a traceback — losing every other card's findings. The comment directly above the fallback line already promises the opposite: that such a card is still checked on its slug."
status: open
stage: null
contribution: medium
created: "2026-07-31T05:54:49Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — for all three malformation shapes (unterminated `---`, `status:open` missing space, duplicate mapping key) `scan_deck` returns instead of raising, still reports the clean control card's findings, and still flags the malformed card on its directory slug.
  - [ ] TDD: a regression test in `tests/test_card_authoring_rules.py` plants a card with unparseable frontmatter and a flaggable German slug in a temp deck and asserts `scan_deck` reports it (not raises), and that a sibling clean card's findings survive.
  - [ ] MECHANICAL: `scan_card` in `scripts/check_card_language.py` wraps `parse_frontmatter` in a `try/except FrontmatterError` that falls back to `{}` and emits `WARNING: <card>: <exc>` on stderr, mirroring `engine.load_all_cards` (`goc/engine.py:973-979`); the comment above `setdefault` becomes true rather than aspirational.
  - [ ] PROCESS: sibling sweep recorded in `log.md` — confirm no other repo-local deck-walking script calls `parse_frontmatter` without a net (`scripts/*.py`), and note the result either way.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` stays green and `uv run python scripts/check_card_language.py --check` still reports the real deck clean.
---

# The English-only guard aborts the whole deck scan on one unparseable card

## Location

`scripts/check_card_language.py:216-228` — `scan_card`, called once per card
from `scan_deck` (line 231-237).

## What's broken

`scan_card` calls `parse_frontmatter` bare:

```python
# scripts/check_card_language.py:216-221
def scan_card(readme: Path) -> list[tuple[str, str]]:
    """Return `(field, reason)` pairs for one card README."""
    frontmatter, _body = parse_frontmatter(readme.read_text(encoding="utf-8"))
    # The directory name is the title of record; fall back to it so a card whose
    # frontmatter the parser cannot read is still checked on its slug.
    frontmatter.setdefault("title", readme.parent.name)
```

The comment is the contract: *"a card whose frontmatter the parser cannot read
is still checked on its slug."* The code does not implement it. `setdefault`
only rescues the one benign outcome — `parse_frontmatter` returning
`({}, text)` because there is no opening `---` at line 1 at all. The engine
documents a second outcome for exactly the case the comment names:

```python
# goc/engine.py:176-180
      - No opening `---` at line 1  → returns ({}, text) (non-frontmatter file)
      - Opening present, closing missing/unparseable → raises FrontmatterError
      - Both delimiters present, YAML valid → returns (data, body)
```

So when the frontmatter genuinely *cannot be read*, `scan_card` raises. And
because `scan_deck` is a single comprehension, the raise escapes the whole walk:

```python
# scripts/check_card_language.py:231-237
def scan_deck(deck_dir: Path = DECK_DIR) -> list[tuple[str, str, str]]:
    """Return `(card, field, reason)` triples for every non-English finding."""
    return [
        (readme.parent.name, field, reason)
        for readme in sorted(deck_dir.glob("*/README.md"))
        for field, reason in scan_card(readme)
    ]
```

One bad card therefore costs three things: the guard's verdict on that card
(whose slug is usually flaggable — that is the whole point of the fallback),
the guard's verdict on **every other card in the deck**, and the clean error
message. Every sibling deck-walker already takes the opposite posture —
`engine.load_all_cards` warns and continues, `engine.validate_deck_directories`
collects the error and continues, and `_cmd_migrate_list_style` was fixed to do
the same by
[goc-migrate-list-style-crashes-on-first-malformed-card-mid-iteration](../goc-migrate-list-style-crashes-on-first-malformed-card-mid-iteration/).
That card's `PROCESS` sibling sweep was scoped to `goc/engine.py`, so this
repo-local script was never in range.

## Empirical evidence

`uv run python .game-of-cards/deck/card-language-guard-aborts-the-whole-deck-scan-on-one-unparseable-card/reproduce.py`
(tracebacks elided; they interleave on stderr):

```
control card alone -> 4 finding(s)

[unterminated] flag_text('kartei-pruefung-fehlt-unterminated') -> ["German '-ung' ending on token 'pruefung'", "German marker word 'fehlt'"]
[unterminated] FAIL scan_deck raised FrontmatterError: frontmatter unterminated: opening '---' at line 1 has no matching closing '---' delimiter

[missing-space] flag_text('kartei-pruefung-fehlt-missing-space') -> ["German '-ung' ending on token 'pruefung'", "German marker word 'fehlt'"]
[missing-space] FAIL scan_deck raised FrontmatterError: YAML parse error inside frontmatter: line 2: 'status:open' is not a valid 'key: value' mapping entry (a ':' key separator must be followed by a space); breaking here would silently drop it and every following key

[duplicate-key] flag_text('kartei-pruefung-fehlt-duplicate-key') -> ["German '-ung' ending on token 'pruefung'", "German marker word 'fehlt'"]
[duplicate-key] FAIL scan_deck raised FrontmatterError: YAML parse error inside frontmatter: line 3: duplicate mapping key 'status'; the earlier value would be silently discarded

3 failing case(s) of 3
```

`flag_text` on each malformed card's slug returns two findings, so the
fallback the comment promises would have caught all three German titles. The
guard dies instead. The control card (`cache-wird-nicht-geleert`, four
findings on its own) contributes zero findings in every failing run — its
verdict is collateral damage.

## Why it matters

The reachability path is hand-editing, not the engine. Every emitter path
(`goc new`, `goc status`, `goc done`, `goc quality-pass`) writes frontmatter
`yaml_lite` can read back, so a malformed card comes from a human or agent
editing `README.md` directly — explicitly permitted by AGENTS.md § "Card
authoring rules" ("when editing frontmatter by hand, follow the same
convention"). All three shapes in the reproducer are ordinary editing slips:
a truncated write, `status:open` without the space, and a duplicated key from
a copy-paste. The duplicate-key shape only became fatal in `ff0fb227`
("reject a key repeated in the same mapping"), which converted a
previously-parseable card into a `FrontmatterError` card — so this crash
surface *widened* two commits ago.

The consequences are all in the guard's two invocation paths:

- The `card-language` pre-commit hook (`.pre-commit-config.yaml`) — which
  `goc new --commit` also triggers, because goc's auto-commit shells out to
  `git commit` without `--no-verify` — dies with a Python traceback naming
  `FrontmatterError` instead of the language rule it exists to enforce. The
  author is told nothing about English-only and nothing about which of the
  other 690+ cards might also be non-English.
- `tests/test_card_authoring_rules.py:391` calls `guard.scan_deck()` against
  the real deck, so the same card turns that suite into an ERROR (a raised
  exception) rather than a FAIL with a readable message.

Neither path loses data, and `goc validate` still reports the malformation
authoritatively — `validate_deck_directories` catches `FrontmatterError` per
card and exits 1 (`goc/engine.py:1283-1287`). That is precisely why the
language guard should *not* re-report it: the malformation already has an
owner. The guard's job is language, and it should keep doing that job on the
slug and on every other card.

## Fix

In `scripts/check_card_language.py`, net the parse in `scan_card` — the same
shape `engine.load_all_cards` uses at `goc/engine.py:973-979`:

```python
from goc.engine import FrontmatterError, parse_frontmatter

def scan_card(readme: Path) -> list[tuple[str, str]]:
    """Return `(field, reason)` pairs for one card README."""
    try:
        frontmatter, _body = parse_frontmatter(readme.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        # Unreadable frontmatter is `goc validate`'s finding, not this guard's:
        # warn, keep the slug check, and let the rest of the deck be scanned.
        print(f"WARNING: {readme.parent.name}: {exc}", file=sys.stderr)
        frontmatter = {}
    frontmatter.setdefault("title", readme.parent.name)
    ...
```

Exit code stays language-only: a warning does not turn `--check` red, so a
malformed card fails the build through `goc validate` (which owns that
diagnostic) and not twice through the language hook.
