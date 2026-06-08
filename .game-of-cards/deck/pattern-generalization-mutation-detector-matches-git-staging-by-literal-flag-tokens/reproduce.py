"""Reproduce: the pattern-generalization Stop hook misses bundled short
`git add` flags because it recognizes staging by exact-equality token match.

`git add -Au` is exactly `git add -A -u`, but the matcher tests each token
for `tok in _BROAD_STAGING_FLAGS`, and `-Au` is not a member, so the broad
mutation is not recognized and the generalization reminder never fires.

Exits non-zero while the bug is live (any bundled-flag form returns False).
"""

import importlib.util
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def _load_hook():
    root = _repo_root()
    hook = root / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"
    spec = importlib.util.spec_from_file_location("pgc_repro", hook)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    f = _load_hook()._is_broad_git_mutation

    # (command, expected) — bundled forms SHOULD be recognized as broad
    bug_cases = [
        ("git add -Au", True),
        ("git add -uA", True),
        ("git add -Ap", True),
    ]
    baselines = [
        ("git add -A -u", True),
        ("git commit -m x", True),
        ("git add -A", True),
        ("git add .", True),
        ("git add path/foo.py", False),
        ("git add -- foo.py", False),
        ("git status", False),
    ]

    bug_live = False
    for cmd, expected in bug_cases + baselines:
        got = f(cmd)
        tag = ""
        if got != expected:
            tag = "  <-- BUG: should be %s" % expected
            if (cmd, expected) in bug_cases:
                bug_live = True
        print("%-6s %-22s%s" % (str(got), cmd, tag))

    print()
    if bug_live:
        print("FAIL: bundled-flag git-add staging is NOT recognized as broad mutation")
        return 1
    print("PASS: all git-add staging spellings recognized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
