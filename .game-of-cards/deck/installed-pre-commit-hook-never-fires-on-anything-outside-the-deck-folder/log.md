## 2026-08-25T04:53:06Z — Closure

- **What changed**: `goc/install.py:79` — `PRE_COMMIT_HOOK` drops
  `files: ^\.game-of-cards/deck/.*$` for `always_run: true`, so the whole-tree
  `goc validate` gate a consuming repo installs fires on every commit instead
  of only on deck edits.
- **Verification**: `reproduce.py` went from exit 1 with 4 of 5 validated
  surfaces unreachable to exit 0 with all 5 firing. The new
  `ShippedPreCommitHookReachability` case fails 7 assertions when pointed at
  the pre-fix literal, so it pins the shape rather than restating it.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1037 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`, 65.8s)

Two things worth carrying forward.

The migration half of the DoD cost nothing. The card expected
`_refresh_goc_validate_block` to need extending to recognise a `files:`-gated
block, by analogy with the glob substitution it was written for in
`goc-upgrade-leaves-stale-pre-commit-validate-pattern`. It was already general:
it matches the GoC-signature stanza and re-emits `PRE_COMMIT_HOOK` wholesale,
so it carries *any* template change forward. Writing the earlier fix as
"re-emit the current literal" instead of "replace this glob with that glob" is
what made this one a one-line edit — the same choice is what will absorb the
next change to the stanza.

The test landed next to the sibling card's, not next to the code it guards.
`tests/test_precommit_hook_reachability.py` already held the invariant and a
`parse_hooks` / `triggers` pair implementing pre-commit's trigger rule; the
shipped literal is a second config subject to the same rule, so it reuses both
rather than restating them in `test_install.py`. Both configs now fail the same
assertion for the same reason.

Assertions in `test_install.py` and
`test_upgrade_precommit_refresh_at_same_version.py` that hard-coded the
migrated glob were rewritten to compare against `PRE_COMMIT_HOOK` itself, so
the next change to the stanza does not require editing them.

Amended the Location quote in the parked card
`install-writes-pre-commit-entry-that-fails-on-plugin-only-hosts`, which
reproduced the old literal verbatim. Its defect (`entry: goc validate` not
resolving on plugin-only hosts) is untouched — it now fires on every commit
rather than only on deck edits, which makes that card more visible, not less.
No supersessions: a sweep of the 15 other open cards mentioning the hook found
none describing this defect.

## Closure verification (2026-08-25T04:53:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-25 — Closure' present
