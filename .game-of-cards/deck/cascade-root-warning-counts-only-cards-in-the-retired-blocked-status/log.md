## 2026-11-09T04:34:53Z — Closure

- **What changed**: `goc/engine.py:2724-2750`: the CASCADE_CHAIN_ROOT walk
  in `validate_blocker_coherence` counts and passes through every live
  descendant (not terminal, not a draft) instead of only `status ==
  "blocked"` ones. The root must itself be live as well as gated, and a
  cycle back to the root no longer counts it. The message now reads
  `N cards cannot close until this one does (gate=<gate>)`, prefix
  unchanged. `goc/engine.py:2648-2684`: the docstring calls STALE_BLOCKED
  and ORPHAN_BLOCKED migration aids, drops the "let the queue hide it"
  sentence, and describes CASCADE_CHAIN_ROOT by the closure gate.
  `goc/templates/skills/card-schema/reference.md:151-158`: § Three-axis
  model names CASCADE_CHAIN_ROOT as the finding that outlives the
  migration. Mirrors regenerated, OpenClaw re-ported.
  `tests/test_validate_blocker_coherence.py`: cascade fixtures rebuilt on
  `open`/`active` cards; the module goes from 11 to 17 tests.
- **Verification**: `reproduce.py` exit 1 before the fix, 0 after. The new
  module run against the pre-fix engine fails exactly its 3 positive tests
  (threshold on `open` cards, `open`/`active`/`blocked` mix, transitive
  `open` chain); all 17 pass on the fix. Seven mutants of the fixed walk
  each fail at least one test. `uv run goc validate` exits 0 and this
  repo's deck now prints **1** CASCADE_CHAIN_ROOT warning (0 before the
  fix), the one predicted at filing:
  `deck-auto-commit-ignores-card-files-other-than-readme-and-log: 3 cards cannot close until this one does (gate=decision)`.
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` are clean.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1475 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`)
- **Bundled with**: none
- **Beyond the filed plan**: the root-liveness check and the cycle guard
  (Fix items 2 and 3, one added DoD box). Record hygiene: the open
  `advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks`
  quoted the rewritten docstring, so its README paragraph was replaced and
  its `log.md` records why. The card that introduced the class,
  `goc-validate-warns-on-stale-blocked-orphan-blocked-and-cascade-roots`,
  got a forward pointer in its README and a post-close amendment in its
  `log.md`.

## Closure verification (2026-11-09T04:37:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-11-09T04:34:53Z — Closure' present
