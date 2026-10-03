## 2026-10-03T04:33:00Z — Resumed

The 2026-10-02 pull-card run filed and claimed this card while closing
`cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it`.
That run's closure log says this card would be fixed through next, but the
run ended first. The card stayed `active` with 0/4 DoD and no
`reproduce.py`, although the body quoted that script's output. Pull-card
runs share one concurrency group, so no other session held the claim, and
the session-start hook listed it as resumable. This run resumed it as its
single pull instead of claiming a new card.

`reproduce.py` was written from the body's description. On the pre-fix
engine it printed the body's quoted output line for line and exited 1.

## 2026-10-03T04:45:20Z — Closure

- **What changed**:
  - `goc/install.py` `_strip_claude_vendored_harness`: new `probe` keyword
    and a bool return. The function works out the GoC skill dirs, hook/shim
    files and settings entries once; the probe reports whether any exist
    without touching anything.
  - `goc/install.py` `_strip_goc_settings_entries`: new `probe` keyword and
    a bool return. The probe skips the write and the warnings.
  - `goc/install.py` `upgrade()`: `needs_vendored_cleanup` comes from that
    probe instead of `(target / ".claude/skills").is_dir()`. The prompt and
    the dry-run note say "GoC files from a prior vendored install".
  - `AGENTS.md`: the switch paragraph and the upgrade-contract paragraph.
  - The three plugin engine mirrors were re-synced by
    `scripts/sync_plugin_assets.py`.
- **Verification**:
  - `reproduce.py`: exit 1 before the fix, exit 0 after. In repo A the
    routine upgrade's offer goes from True to False and its no-op verdict
    from False to True. In repo B the offer goes from False to True, and
    the leftovers go from 3 scripts and 3 entries to none.
  - All four new tests fail against the pre-fix `goc/install.py` (a
    temporary worktree at `HEAD`): 2 failures and 2 errors.
  - The open sibling's `reproduce.py`
    (`plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove`)
    still exits 1 with the same output, so its defect is unchanged.
  - `goc validate`, `sync_plugin_assets.py --check`,
    `check_card_language.py --check` and
    `check_card_frontmatter_yaml.py --check` are clean.
- **Audit**: no rubric configured; mechanical fix. It applies the
  convention in `AGENTS.md` § "`.game-of-cards/` ownership model and
  `goc upgrade` contract": an upgrade-time work signal asks its executor in
  `probe=True` mode instead of restating it. The cleanup offer was the one
  remaining term next to the plan that still restated its executor.
- **Project impact**: a repo that switched to the plugin and keeps skills
  of its own gets a quiet `goc upgrade` again. A repo whose only leftovers
  are GoC hooks and settings entries is now offered the cleanup that
  `goc validate`'s double-fire warning points it to.
- **Tests**: 1215 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-10-03T04:46:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-03 — Closure' present
