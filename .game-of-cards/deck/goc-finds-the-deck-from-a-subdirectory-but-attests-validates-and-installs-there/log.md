## 2026-09-28T01:27:59Z — Filed (audit-deck)

Found while auditing which "project root" each surface uses after
3e17e3b3 taught `_resolve_deck_root` to walk upward from a subdirectory.
`reproduce.py` confirms 8 diverging surfaces and exits 1.

I checked the fix with a throwaway patch in a scratch clone. Nothing from
that patch is committed. It was about 30 lines covering Fix steps 1–3:

- re-derive `REPO_ROOT` from `DECK_ROOT` when `DECK_ROOT` encloses cwd;
- make `install()` / `upgrade()` resolve `target` through
  `_resolve_deck_root`;
- add a bounded upward walk to both hooks.

With that patch, `reproduce.py` exits 0 and reports all 8 surfaces the
same. The full suite under the patch ran 1197 tests. It had 1 failure,
`test_plugin_mirror_parity.PluginMirrorParityTest.test_real_repo_passes`,
because the scratch patch did not re-sync the plugin mirrors. It had 3
errors, `PackageNotFoundError: game-of-cards` in `tests/test_install.py`.
The same 3 errors appear on an unmodified clone run with a bare `python3`
and no installed distribution, so they are unrelated to the patch. No
behavioral test pins the cwd-as-root semantics, so none failed. That gap is
why the DoD asks for new tests, not only a green `reproduce.py`.

## 2026-10-01T04:37:55Z — Closure

Resumed from the 2026-09-30 claim. That run hit the pull-card job's
30-minute timeout before committing anything.

- **What changed**: `goc/engine.py` `_resolve_project_roots` is now the one
  derivation of `REPO_ROOT` and `DECK_ROOT`. `REPO_ROOT` is `DECK_ROOT`
  except under the shared-deck redirect, where it is the linked worktree's
  `git rev-parse --show-toplevel`. `_resolve_deck_root` wraps it, with the
  redirect split out as `_shared_worktree_deck_root` and the walk as
  `_walk_to_deck_root`. `goc/install.py` `_project_target()` gives
  `install()` / `upgrade()` the same root. Both runtime hooks gained a
  mirrored `_find_project_dir` walk, and pattern-check now uses the
  session-start input precedence (hook `cwd` first). `goc.md:70` now
  extends the any-nested-directory promise to attest, validate, upgrade and
  install, and names the shared-deck exception.
- **Verification**: `reproduce.py` exits 0: all 8 surfaces from `src/pkg/`
  agree with the root run. The new
  `tests/test_project_root_from_subdirectory.py` (7 tests) passes. On a
  detached worktree of 08508b68 (pre-fix) it fails 6 and errors 10, so every
  test catches the defect. `goc validate` exits 0 from the root and from
  `scripts/`. `sync_plugin_assets.py --check` is clean.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1204 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`)
- **Deviation from the filed plan**: the installer targets `REPO_ROOT`, not
  `DECK_ROOT`. The two are identical except under the shared-deck redirect.
  There, `install` / `upgrade` must write the linked checkout's tracked
  files, not the primary tree's.

## Closure verification (2026-10-01T04:37:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-10-01 — Closure' present
