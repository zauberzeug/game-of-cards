"""Reproduce: pattern_generalization_check._had_code_mutation overmatches `git add -- <path>`.

Builds four single-turn synthetic JSONL transcripts whose only assistant
tool call is a Bash invocation with a known git command, then asks
`_had_code_mutation` whether the turn counted as a code mutation.

Expected behavior (per the hook docstring "git-commit" intent and
AGENTS.md's pathspec-separator staging discipline):
  - `git commit -- foo.py`  -> True   (a commit)
  - `git add -A`            -> True   (directory-wide flag form)
  - `git add foo.py`        -> False  (bare path, no mutation in this turn)
  - `git add -- foo.py`     -> False  (pathspec-separator staging — not a commit)

Actual behavior printed below: row 4 reports True instead of False, because
the constant `BASH_COMMIT_TOKENS = (..., "git add -", ...)` is matched via
plain substring containment (`tok in cmd`), so `"git add -"` matches
`"git add -- foo.py"`.
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
    """Load the hook script as a module by file path (it isn't on sys.path)."""
    hook_path = REPO / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"
    spec = importlib.util.spec_from_file_location("pgc", hook_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {hook_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _transcript_for(cmd: str) -> str:
    """Write a single-line JSONL transcript with one assistant Bash turn."""
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
        ("git commit -- foo.py", True),
        ("git add -A", True),
        ("git add foo.py", False),
        ("git add -- foo.py", False),
    ]

    print(f"{'command':<30} {'expected':<10} {'actual':<10} verdict")
    print("-" * 64)
    fails = 0
    for cmd, expected in cases:
        path = _transcript_for(cmd)
        actual = pgc._had_code_mutation(path)
        verdict = "ok" if actual == expected else "DEFECT"
        if verdict == "DEFECT":
            fails += 1
        print(f"{cmd!r:<30} {str(expected):<10} {str(actual):<10} {verdict}")

    print()
    if fails:
        print(
            f"FAIL: {fails} row(s) diverged from intended behavior. "
            "See `BASH_COMMIT_TOKENS` substring match in "
            "goc/templates/hooks/pattern_generalization_check.py:23,73."
        )
        return 1

    print("PASS: matcher rejects pathspec-separator staging.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
