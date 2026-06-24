"""Reproduce: closure_on_integration conflates a git error (exit 128) with
genuinely-not-integrated (exit 1).

_enforce_closure_on_integration_or_exit tests `git merge-base --is-ancestor`
with `!= 0`, so a git error (128) is treated identically to a true
non-ancestor (1): both block closure with the misleading "HEAD is not
reachable from origin/main" message and `sys.exit(2)`.

A git error should warn-and-skip (fail open), matching the sibling
fetch-failure branch directly above it. Exit 1 should still block.

PASS (defect fixed): exit 128 -> warn-and-skip (no SystemExit); exit 1 ->
block (SystemExit 2); exit 0 -> allow (no SystemExit).
FAIL (defect present): exit 128 -> SystemExit (wrongly blocked).
"""

import io
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine


def _run_with_merge_base_rc(rc: int):
    """Invoke the closure check with config enabled, deck git-tracked, fetch
    succeeding, and merge-base returning exit code `rc`. Returns
    ("exit", code) if it called sys.exit, else ("ok", None)."""
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if cmd[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd[:2] == ["git", "merge-base"]:
            return SimpleNamespace(returncode=rc, stdout=b"", stderr=b"")
        return real_run(cmd, *args, **kwargs)

    orig_run = engine.subprocess.run
    orig_cfg = engine.load_deck_config
    orig_tracked = engine._deck_is_git_tracked
    engine.subprocess.run = fake_run
    engine.load_deck_config = lambda: {"workflow": {"closure_on_integration": True}}
    engine._deck_is_git_tracked = lambda: True
    buf = io.StringIO()
    try:
        with redirect_stderr(buf):
            engine._enforce_closure_on_integration_or_exit("demo-card")
        return ("ok", None)
    except SystemExit as exc:
        return ("exit", exc.code)
    finally:
        engine.subprocess.run = orig_run
        engine.load_deck_config = orig_cfg
        engine._deck_is_git_tracked = orig_tracked


def main() -> int:
    rc0 = _run_with_merge_base_rc(0)
    rc1 = _run_with_merge_base_rc(1)
    rc128 = _run_with_merge_base_rc(128)

    print(f"merge-base exit 0   (integrated)      -> {rc0}")
    print(f"merge-base exit 1   (not an ancestor) -> {rc1}")
    print(f"merge-base exit 128 (git error)       -> {rc128}")

    ok_0 = rc0 == ("ok", None)
    ok_1 = rc1 == ("exit", 2)
    ok_128 = rc128 == ("ok", None)

    print()
    print(f"exit 0   allows closure:        {'PASS' if ok_0 else 'FAIL'}")
    print(f"exit 1   blocks closure (2):    {'PASS' if ok_1 else 'FAIL'}")
    print(f"exit 128 warns & skips:         {'PASS' if ok_128 else 'FAIL'}")

    if ok_0 and ok_1 and ok_128:
        print("\nPASS: git error is no longer conflated with not-integrated.")
        return 0
    print("\nFAIL: a git error (exit 128) is wrongly treated as not-integrated.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
