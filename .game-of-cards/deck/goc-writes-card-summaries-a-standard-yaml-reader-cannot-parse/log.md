## 2026-08-30T04:52:00Z — Closure

- **What changed**: `goc/engine.py:224` — `_YAML_INDICATORS` transcribes YAML
  1.2 §5.3's closed `c-indicator` list, split into `_YAML_INDICATOR_FIRST`
  (16 chars, illegal at position 0 whatever follows) and
  `_YAML_SPACE_BOUND_INDICATORS` (`-`, `?`, `:`, binding only before a
  space/TAB or standing alone). `_opens_with_yaml_indicator` (:264) applies the
  split and `_yaml_inline` (:358) consults it instead of `frozenset("&*")`; TAB
  joined `_YAML_NEEDS_QUOTE` (:214) because it is illegal anywhere in a plain
  scalar. `scripts/check_card_frontmatter_yaml.py` imports both sets from
  `goc.engine` (:90) rather than restating them and flags the TAB case (:148).
  The two false remediation claims — the guard's failure message (:198) and
  `AGENTS.md:493` — are now true and say why.
- **Verification**: `reproduce.py` exits 0 (was 1) — 7/7 values emit quoted,
  all 7 still round-trip faithfully through `yaml_lite`, and a hand-quoted
  value survives re-emission. 1047 tests pass (was 1037 + this card's 10).
  `uv run goc validate` exit 0, 740 cards OK. Guard: "strict-YAML clean
  (740 cards scanned)". `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` both OK.
- **Sensitivity**: reverting the emitter trigger to `frozenset("&*")` produces
  21 failures in `tests/test_emitter_strict_yaml_quoting.py`; re-hardcoding the
  guard's tuple with `!` dropped produces 23. The spec list is enumerated
  independently in the test, so shrinking `engine._YAML_INDICATORS` fails there
  rather than quietly shortening the loops.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is
  empty); mechanical fix. The one judgement it encodes is the oracle: the
  emitter's contract is "output any YAML reader accepts", not "output
  `yaml_lite` survives", so the trigger is derived from the YAML spec and not
  from parser behaviour. That is the counter-evidence this card was filed to
  carry, now amended onto
  `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`.
- **Deck impact**: none — the deck was guard-clean before and after
  (739 → 740 cards, zero findings), so no card on disk re-emits differently.
  The change alters only what future emits produce.
- **Tests**: 1047 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a. `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`
  covers the adjacent *quoted*-scalar blind spot and stays open at
  `human_gate: decision`; this fix neither closes nor touches it.

## Closure verification (2026-08-30T04:42:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-08-30 — Closure' present
