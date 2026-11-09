## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/install.py:1322`
(`def _append_precommit_hook(target: Path) -> None:`), moved by `0be57d4d`
(signature gained `*, probe: bool = False`, returns bool).
Reproducer: `reproduce.py` → exit 1, "[FAIL] plugin-default install wrote a pre-commit entry that cannot execute on this host".
Verdict: still live. Re-anchored `goc/install.py:1571` → `:1657` (`def _append_precommit_hook(`).
Gate unchanged.

## 2026-11-09T02:25:07Z — DoD named helpers that never existed

The DoD's fourth item and § Decision required credited the stanza migration
to `_migrate_precommit_validate_pattern` / `_precommit_hook_drifted`. Neither
name has ever been in the code: `git log -G` finds both only in this card's
filing commit `7a09e1b4`. The `files:` glob migration they describe is
`_refresh_goc_validate_block` (`goc/install.py:1627`, from `2ec9943b`), which
`_append_precommit_hook` runs on install and upgrade. Both references now
name it. The body also notes the one constraint that matters for this card:
the refresh only touches a single-hook stanza whose entry is
`goc validate`. Gate, options and DoD scope unchanged.
