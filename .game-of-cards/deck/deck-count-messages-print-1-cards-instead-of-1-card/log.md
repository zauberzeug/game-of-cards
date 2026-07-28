## 2026-07-27T01:26:52Z — Closure

- **What changed**: `goc/engine.py:1200` — added `_cards_noun(count)` (the
  `render_active_notice` ternary, factored to one definition) and routed all
  seven hardcoded-plural count banners plus `render_active_notice` itself
  through it; `tests/test_count_message_pluralization.py` added as the CI drift
  guard; `reproduce.py`'s `SAFE_TERNARY` classifier widened to recognize the
  helper (FAIL predicate untouched).
- **Verification**: `reproduce.py` exit 0 — 7 plural-unsafe sites → 0, 9
  plural-safe ternary sites (1 definition + 8 call sites), 3 `card(s)` sites in
  `migrate` left as-is. One-card scratch deck now prints `Quality pass over 1
  card` and `— 1 card`; real 169-card deck still prints `169 cards`. Guard
  falsified on purpose: reverting `Bundled close:` to the hardcoded plural made
  the new test fail and name `goc/engine.py:4408`, then the revert was undone.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is
  scaffold-only); mechanical fix.
- **Choice**: took the ternary over `card(s)` — most of the seven banners are
  prose, where `3 card(s)` reads like a hedge, and `render_active_notice` (the
  closest neighbour in intent) already used the ternary. Factoring it into a
  helper rather than pasting it eight times is the same convention with one
  definition, not the "third form" the DoD warned against; `tests/test_install.py`
  asserts `ACTIVE: 1 claimed card` and still passes untouched, which pins the
  rendered wording as unchanged.
- **DoD addition**: a fourth `GUARD` box was added at closure. The original DoD
  designated the card's `reproduce.py` as the TDD artefact, but it lives in the
  deck and CI never runs it — so as filed, the sweep would have shipped with no
  protection against drifting back one site at a time, which is precisely the
  failure mode that made this a seven-site sweep instead of a point fix.
- **Project impact**: n/a
- **Tests**: 800 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`); `uv run goc validate` exit 0.

## Closure verification (2026-07-27T01:27:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-27 — Closure' present

## 2026-07-27T01:34:00Z — Post-close amendment

- **Forward pointer**: filed
  `count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box`
  minutes after closure. The Stop-hook generalization prompt triggered a
  re-scan with a looser regex, which found nine hardcoded-plural count
  interpolations this card's fix set never contained.
- **Why this card's scan missed them**: the fix set was defined by
  `\{len\([^)}]*\)\}\s+cards?\b` — the noun had to be the bare word `cards`
  immediately after the interpolation. That excludes every non-card noun
  (`boxes`, `titles`, `summaries`, `items`, `lines`) and also
  `{len(cluster)} blocked cards` at `goc/engine.py:2240`, where the adjective
  `blocked` sits between count and noun. So one *card* banner was left unfixed
  by a card-noun sweep.
- **The guard inherits the hole**: `tests/test_count_message_pluralization.py`
  uses the same immediately-adjacent pattern, so it reports the convention as
  enforced while nine interpolations sit outside its reach. Repairing the guard
  is a DoD item on the successor.
- **Not a retraction**: this card's stated scope (the bare-`cards` noun, seven
  sites) is complete and correct; the README's completeness claim was narrowed
  in place to say so explicitly rather than left to imply full coverage.
