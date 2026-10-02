## 2026-10-02T04:38:00Z — Hypothesis verified

Claimed from the ready queue. A scratch `goc install --local-skills` repo
holding `.claude/skills/my-own-skill` reproduced both halves. Applying the
old `goc.md` recipe literally deleted the user skill. `goc upgrade </dev/null`
then brought back 16 GoC skill dirs plus `_goc-bootstrap.sh`, 3 hook scripts
and 3 settings hook events, with the pin still `skills_source: vendored`.
`goc validate` was silent: with no plugin enabled, its double-fire check has
nothing to fire on. Neither escape in the falsification recipe fired, so the
`unverified` tag comes off.

The supported switch kept `my-own-skill` and pinned `plugin`. Two side
findings came out of that run:

- A second `goc upgrade` offered the cleanup again, because `.claude/skills/`
  still existed. Filed as
  `upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills`
  and fixed through after this closure.
- Through `claude-plugin/bin/goc`, the cleanup kept all 16 GoC skill dirs.
  Filed as
  `plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove`
  and left open. `goc.md` carries a standalone-`goc` caveat until it lands.

A grep for the same claim across the tree found one more copy of a
hand-delete switch: `goc validate`'s double-fire remedy ("switch to
skills_source: plugin and remove .claude/hooks/"). It was fixed in the same
change and added as a fourth DoD box.

## 2026-10-02T04:49:46Z — Closure

- **What changed**:
  - `goc.md` § "Coexistence with the repo-local harness": the hand-delete
    recipe is replaced by the numbered switch (set `skills_source: plugin`,
    then run `goc upgrade` and answer `y`). The section also says what the
    cleanup keeps, carries the standalone-`goc` caveat, and warns that a
    hand-delete is re-vendored.
  - `goc/engine.py` `validate_plugin_hook_double_fire`: the remedy routes
    through `goc upgrade`'s cleanup. Mirrored into the three plugin payloads
    by `sync_plugin_assets.py`.
  - New guard `tests/test_plugin_switch_recipe.py` (5 tests).
  - `tests/test_validate_plugin_hook_double_fire.py` pins the remedy.
- **Verification**:
  - `reproduce.py` exits 1 on the pre-fix text (`git show 5be726c7:goc.md`):
    user skill lost; 16 skill dirs, 3 hook scripts and 3 settings entries
    re-vendored; pin `vendored`.
  - It exits 0 on the fixed text: pin `plugin`, zero GoC layout, user skill
    intact after a routine upgrade.
  - All 5 guard tests fail when pointed at the pre-fix `goc.md`.
  - `goc validate`, `check_card_language.py --check` and
    `check_card_frontmatter_yaml.py --check` are clean.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is
  empty). The fix is not purely mechanical. It applies this repo's
  doc-accuracy convention that a shipped instruction is executed against
  the engine, not restated beside it. It adds the third implementation of
  the run-it-against-a-fixture technique, the first one aimed at a
  human-facing page, which
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
  names as a guard class its pending decision has yet to adopt. That card
  now lists this one as its twenty-fourth instance.
- **Project impact**: the CLI reference and `goc validate` now give a
  vendored consumer a switch that keeps their own skills and survives the
  next upgrade. Two known rough edges are tracked: the bundled-engine gap
  (`plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove`,
  open) and the re-offered prompt
  (`upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills`,
  fixed through next).
- **Tests**: 1211 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-10-02T04:50:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-02 — Closure' present
