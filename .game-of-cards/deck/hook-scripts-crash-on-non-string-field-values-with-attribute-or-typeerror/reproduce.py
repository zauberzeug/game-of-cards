"""Reproduce: hook scripts crash on non-string field values.

The closed predecessor `hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror`
added isinstance(data, dict) guards at the top level of both hooks. But the
field values inside the dict are still unguarded: a dict-shaped payload with a
non-string `prompt` or `transcript_path` value crashes the hook.

Expected after fix: rc == 0 from both hooks on the non-string-field inputs.
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


REPO = _repo_root()
ROUTER = REPO / "goc" / "templates" / "hooks" / "deck_prompt_router.py"
PG_CHECK = REPO / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"


def run(hook: Path, stdin_payload: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(hook)],
        input=stdin_payload,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr


def main() -> int:
    failures: list[str] = []

    rc, err = run(ROUTER, '{"prompt": 123}')
    print(f"deck_prompt_router.py with non-string prompt: rc={rc}")
    if rc != 0:
        print("  stderr:", err.strip().splitlines()[-1] if err.strip() else "(empty)")
        failures.append("deck_prompt_router.py crashed on non-string prompt")

    rc, err = run(PG_CHECK, '{"transcript_path": 123}')
    print(f"pattern_generalization_check.py with non-string transcript_path: rc={rc}")
    if rc != 0:
        print("  stderr:", err.strip().splitlines()[-1] if err.strip() else "(empty)")
        failures.append("pattern_generalization_check.py crashed on non-string transcript_path")

    if failures:
        print()
        print("DEFECT REPRODUCED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print()
    print("OK: both hooks return 0 silently on non-string field values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
