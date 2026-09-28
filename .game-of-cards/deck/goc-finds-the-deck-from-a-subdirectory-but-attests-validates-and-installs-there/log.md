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
