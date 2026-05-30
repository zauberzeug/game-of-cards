"""Reproduce: pattern_generalization_check._had_code_mutation skips NotebookEdit.

Builds single-turn synthetic JSONL transcripts whose only assistant tool
call is one of `Edit`, `Write`, `NotebookEdit`, or `Read`, then asks
`_had_code_mutation` whether the turn counted as a code mutation.

Expected behavior (the hook's intent: fire on any code-mutating tool
call). Claude Code's mutating-tool surface includes `NotebookEdit` for
Jupyter notebook cells alongside `Edit` and `Write` for source files:

  Positive (must fire the generalization reminder):
    - `Edit`           -> True
    - `Write`          -> True
    - `NotebookEdit`   -> True   (mutates .ipynb cells; same intent as Edit)

  Negative (must NOT fire — non-mutating tools):
    - `Read`           -> False

Actual behavior printed below: the `NotebookEdit` row reports False
because `CODE_MUTATING_TOOLS = frozenset({"Edit", "Write"})` at
goc/templates/hooks/pattern_generalization_check.py:22 omits it.
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


def _transcript_for(tool_name: str) -> str:
    entry = {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "name": tool_name,
                "input": {},
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
        # positive baseline (must stay True after fix)
        ("Edit", True),
        ("Write", True),
        # the defect row
        ("NotebookEdit", True),
        # negative baseline (must stay False after fix)
        ("Read", False),
    ]

    print(f"{'tool':<20} {'expected':<10} {'actual':<10} verdict")
    print("-" * 50)
    fails = 0
    for tool, expected in cases:
        path = _transcript_for(tool)
        actual = pgc._had_code_mutation(path)
        verdict = "ok" if actual == expected else "DEFECT"
        if verdict == "DEFECT":
            fails += 1
        print(f"{tool:<20} {str(expected):<10} {str(actual):<10} {verdict}")

    print()
    if fails:
        print(
            f"FAIL: {fails} row(s) diverged from intended behavior. "
            "See `CODE_MUTATING_TOOLS` at "
            "goc/templates/hooks/pattern_generalization_check.py:22."
        )
        return 1

    print("PASS: matcher covers all canonical code-mutating tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
