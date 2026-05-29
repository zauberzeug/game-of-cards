"""Reproduce: `goc` leaks a BrokenPipeError traceback when stdout
closes early.

Runs `uv run goc --done` and reads only the first three lines from
its stdout, then closes the pipe. Reports whether stderr contains a
`BrokenPipeError` traceback. Exits non-zero when the defect fires
(stderr carries the traceback); exits zero once the fix lands.
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


def main() -> int:
    root = _repo_root()
    proc = subprocess.Popen(
        ["uv", "run", "goc", "--done"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    head_lines: list[str] = []
    for _ in range(3):
        line = proc.stdout.readline()
        if not line:
            break
        head_lines.append(line.rstrip("\n"))
    proc.stdout.close()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    err = (proc.stderr.read() if proc.stderr else "") or ""
    print("--- stdout (first 3 lines) ---")
    for line in head_lines:
        print(line)
    print("--- stderr ---")
    print(err.rstrip("\n") or "(empty)")
    has_traceback = "BrokenPipeError" in err
    print("--- verdict ---")
    print(f"defect fires: {has_traceback}")
    return 1 if has_traceback else 0


if __name__ == "__main__":
    sys.exit(main())
