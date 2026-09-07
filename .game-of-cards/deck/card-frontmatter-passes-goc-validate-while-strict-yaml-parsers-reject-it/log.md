# log — card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it

## 2026-08-16T05:00:54Z — Closure

- **What changed**:
  - `.game-of-cards/deck/closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded/README.md:3`
    and `.game-of-cards/deck/repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope/README.md:3`
    — re-emitted through `emit_frontmatter`, which quotes and escapes the two
    plain scalars strict YAML refused.
  - `scripts/check_card_frontmatter_yaml.py` — new repo-local guard: flags a
    plain scalar holding `: ` or opening with a YAML indicator, exempting `|`/`>`
    only as a complete block header via the engine's own `_YAML_BLOCK_HEADER_RE`.
  - `tests/test_card_frontmatter_yaml.py` — 11 tests: both historical offenders
    replayed byte-for-byte, every leading indicator enumerated, the deck's
    legitimate shapes pinned as precision cases, a non-vacuity assertion, and the
    `--check` exit code the pre-commit hook depends on.
  - `.pre-commit-config.yaml` — `card-frontmatter-yaml` hook beside
    `card-language`, so the guard fires on the filing path, not only on push.
  - `AGENTS.md` — the rule and its guard recorded under § Card authoring rules,
    and the script added to § Common commands.
- **Verification**: the guard and PyYAML agree card-for-card across the deck —
  on the pre-fix tree, 2 flagged / 2 refused / 0 false positives / 0 false
  negatives over 721 cards; on the fixed tree, 0 / 0 over 722, and
  `reproduce.py` exits 0. `goc validate` exits 0. Sibling sweep clean: all 99
  shipped `SKILL.md` files and every in-tree `.yaml`/`.yml` file already parse
  under strict YAML, so the card README was the only unguarded frontmatter
  surface.
- **Audit**: no rubric configured; mechanical fix. (`.game-of-cards/hooks/finish-card.md`
  is an empty stub.) The one judgment call — guard in `scripts/` rather than in
  `goc validate` — is settled by precedent, not taste: `goc validate` ships to
  consumers and cannot take back the PyYAML dependency
  `drop-third-party-runtime-dependencies-from-goc` removed, and this repo has
  placed the identical question repo-local twice before
  (`tests/test_skill_frontmatter_strict_yaml.py`, `scripts/check_card_language.py`).
- **Project impact**: n/a
- **Tests**: 985 passed / 1 failed / 0 xfailed. The single failure is
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, red on
  `main` before this work and tracked by the open card
  `regression-suite-red-on-main-over-the-unverified-tag-row`; the suite count
  rose from 975 to 986 with no new failure.
- **Bundled with**: n/a

### Note on the guard's own bug, caught during closure

The first end-to-end run of the guard against a planted offender printed
`clean (1 cards scanned)` and exited `0`. `main` counted cards through the
late-bound `DECK_DIR` global but scanned through `scan_deck`'s default argument,
which binds once at definition — so repointing the module attribute counted one
directory and scanned another. Fixed by passing `DECK_DIR` explicitly, and
pinned by `test_check_exits_nonzero_on_an_offending_deck`, which fails with
exactly the pre-fix symptom when the default-argument form is restored.
`scripts/check_card_language.py:266` carries the same shape; harmless there
because nothing repoints its `DECK_DIR`, and left alone rather than changed as
drive-by scope.

## Closure verification (2026-08-16T05:01:20Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-08-16 — Closure' present
