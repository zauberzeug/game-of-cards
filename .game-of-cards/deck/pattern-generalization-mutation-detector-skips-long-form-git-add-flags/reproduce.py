"""Reproduce: pattern_generalization_check._had_code_mutation skips long-form `git add` flags.

Builds single-turn synthetic JSONL transcripts whose only assistant tool
call is a Bash invocation with a known git command, then asks
`_had_code_mutation` whether the turn counted as a code mutation.

Expected behavior (per the hook docstring intent and `git-add(1)`,
which documents `--all`, `--update`, `--patch` as long-form aliases of
`-A`, `-u`, `-p`):

  Positive (must fire the generalization reminder):
    - `git commit -m msg`     -> True   (any commit)
    - `git add -A`            -> True   (short broad-staging flags)
    - `git add -p`            -> True
    - `git add -u`            -> True
    - `git add .`             -> True   (bare pathspec)
    - `git add --all foo/`    -> True   (long-form alias of -A)
    - `git add --update`      -> True   (long-form alias of -u)
    - `git add --patch`       -> True   (long-form alias of -p)

  Negative (must NOT fire):
    - `git add -- foo.py`     -> False  (pathspec separator)
    - `git add foo.py`        -> False  (bare explicit path)

Actual behavior printed below: the three long-form rows report False
instead of True, because `_BASH_COMMIT_RE`'s staging-flag alternation
`-[A-Za-z]` only matches a single-letter flag.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()
sys.path.insert(0, str(REPO))


def _load_hook_module():
    hook_path = REPO / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"
    spec = importlib.util.spec_from_file_location("pgc", hook_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {hook_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _transcript_for(cmd: str) -> str:
    entry = {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "name": "Bash",
                "input": {"command": cmd},
            }
        ],
    }
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    fh.write(json.dumps(entry) + "\n")
    fh.close()
    return fh.name


def main() -> int:
    pgc = _load_hook_module()

    cases = [
        # short-flag positives (baseline preserved)
        ("git add -A", True),
        ("git add -p", True),
        ("git add -u", True),
        ("git add .", True),
        # long-form positives (the defect rows)
        ("git add --all foo/", True),
        ("git add --update", True),
        ("git add --patch", True),
        # negative baseline (must stay False)
        ("git add -- foo.py", False),
        ("git add foo.py", False),
        # commit positive (baseline)
        ("git commit -m msg", True),
    ]

    print(f"{'command':<28} {'expected':<10} {'actual':<10} verdict")
    print("-" * 64)
    fails = 0
    for cmd, expected in cases:
        path = _transcript_for(cmd)
        actual = pgc._had_code_mutation(path)
        verdict = "ok" if actual == expected else "DEFECT"
        if verdict == "DEFECT":
            fails += 1
        print(f"{cmd!r:<28} {str(expected):<10} {str(actual):<10} {verdict}")

    print()
    if fails:
        print(
            f"FAIL: {fails} row(s) diverged from intended behavior. "
            "See `_BASH_COMMIT_RE` staging-flag alternation in "
            "goc/templates/hooks/pattern_generalization_check.py:28-30."
        )
        return 1

    print("PASS: matcher covers long-form staging flags.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
