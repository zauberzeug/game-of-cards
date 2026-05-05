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
    repo = _repo_root()
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--stage", "foo-bar"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    has_traceback = "Traceback (most recent call last)" in combined or "ValueError:" in combined
    print(f"exit={result.returncode}")
    print(f"traceback={has_traceback}")
    if has_traceback:
        print("defect present: invalid --stage range leaks an internal traceback")
        return 1
    if result.returncode == 0:
        print("defect present: invalid --stage range was accepted")
        return 1
    print("ok: invalid --stage range fails without traceback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
