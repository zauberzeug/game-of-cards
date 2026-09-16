## 2026-09-16T04:44:30Z — Closure

- **What changed**: `.game-of-cards/deck/pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries/README.md:3` — the offending `summary:` re-emitted through `emit_frontmatter` so its interior quotes are escaped (one line; every parsed field, the summary text and the body byte-identical). `tests/test_card_frontmatter_yaml.py` — new `CardSummaryQuotingIsEmitterCanonicalTest` pins already-quoted summaries against the emitter, and the module docstring no longer asserts an unqualified whole-deck zero-false-negative calibration.
- **Verification**: `reproduce.py` exits 0 both ways — 703 quoted summaries scanned, 0 the emitter would write differently; 759 cards scanned under PyYAML, 0 refused-but-clean (was 1 of each). Non-vacuity proved by reverting the repair: `test_live_deck_quoted_summaries_are_emitter_canonical` fails, then passes once restored.
- **Audit**: PASS — no rubric configured; mechanical fix. `.game-of-cards/hooks/finish-card.md` is comment-only.
- **Project impact**: the deck is readable end-to-end by a strict YAML parser again, which is what `Skill(kickoff)` promises every consuming repo. The architectural question — whether `scripts/check_card_frontmatter_yaml.py` should stop skipping quoted values — stays parked on `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`, whose body and log were amended with the materialized instance and whose gate was left up.
- **Tests**: 1151 passed / 0 failed / 0 xfailed (was 1147 before the four added here).
- **Bundled with**: n/a

## Closure verification (2026-09-16T04:44:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-16 — Closure' present
