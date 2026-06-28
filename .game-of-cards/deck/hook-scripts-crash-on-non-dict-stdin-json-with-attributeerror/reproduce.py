"""Reproduce: hook scripts crash on non-dict stdin JSON.

Run from a clean checkout via `uv run python deck/<title>/reproduce.py`
(or `python3 .game-of-cards/deck/<title>/reproduce.py`).

Before the fix: both hooks exit non-zero with an AttributeError
traceback when stdin parses to a list, scalar, or null.
After the fix: both hooks return 0 silently for the same payloads.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
HOOKS = ROOT / "goc" / "templates" / "hooks"
CASES = [
    ("deck_prompt_router.py", "[1,2,3]"),
    ("deck_prompt_router.py", "null"),
    ("deck_prompt_router.py", '"a string"'),
    ("pattern_generalization_check.py", "[1,2,3]"),
    ("pattern_generalization_check.py", "null"),
    ("pattern_generalization_check.py", "42"),
    ("deck_session_start.py", "[1,2,3]"),
]


def _run(hook: str, payload: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )
    err = (result.stderr or "").strip().splitlines()
    tail = err[-1] if err else ""
    return result.returncode, tail


def main() -> int:
    print(f"# Reproduction: non-dict stdin JSON crashes {HOOKS}\n")
    failures = 0
    for hook, payload in CASES:
        rc, tail = _run(hook, payload)
        verdict = "OK" if rc == 0 else "CRASH"
        if rc != 0:
            failures += 1
        print(f"  {verdict:6s}  {hook:36s}  payload={payload!r:14s}  rc={rc}  tail={tail!r}")
    print()
    if failures:
        print(f"DEFECT REPRODUCED: {failures}/{len(CASES)} runs crashed (expected: 0 after fix).")
        return 0
    print("No crashes observed; all hooks tolerated non-dict payloads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
