"""Demonstrate the pre-subcommand-global-options bypass.

The mutation detector at goc/templates/hooks/pattern_generalization_check.py
tokenizes via shlex.split and inspects `tokens[0]` and `tokens[1]`. Every
git invocation prefixed with a pre-subcommand global option (`-c key=val`,
`-C <path>`, `--no-pager`, `-P`, `--git-dir=<path>`) pushes the real
subcommand to `tokens[2+]`, so the detector reports False on shapes that
are unambiguously broad index mutations.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root() / "goc" / "templates" / "hooks"))

from pattern_generalization_check import _is_broad_git_mutation  # noqa: E402


CASES = [
    # (cmd, expected_True_because, actual_to_print)
    ("git -c gpg.sign=false commit -m foo", True),
    ("git -c commit.gpgsign=false commit -m foo", True),
    ("git --no-pager commit -m foo", True),
    ("git -C /tmp/worktree commit -m foo", True),
    ("git --git-dir=/foo commit -m foo", True),
    ("git -P commit -m foo", True),
    # baseline positives still match:
    ("git commit -m foo", True),
    ("git add -A", True),
    ("git add .", True),
    # baseline negatives still rejected:
    ("git add path/to/file", False),
    ("git add -- foo.py", False),
    ("git status", False),
]


def main() -> int:
    defects = 0
    print(f"{'command':<48}  {'expected':<8}  {'actual':<8}  verdict")
    print("-" * 76)
    for cmd, expected in CASES:
        actual = _is_broad_git_mutation(cmd)
        ok = actual is expected
        verdict = "ok" if ok else "DEFECT"
        if not ok:
            defects += 1
        print(f"{cmd!r:<48}  {expected!s:<8}  {actual!s:<8}  {verdict}")
    print()
    if defects:
        print(f"{defects} defect row(s) — exit 1")
        return 1
    print("all rows ok — exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
