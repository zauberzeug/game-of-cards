from __future__ import annotations

import os
import subprocess
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


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "deck").mkdir()
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--status", "bogus"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    combined = f"{result.stdout}\n{result.stderr}"
    print(f"exit={result.returncode}")
    print(f"traceback={'Traceback' in combined}")
    if "Traceback" in combined:
        print("defect present: invalid --status leaks a traceback")
        return 1
    if result.returncode == 0:
        print("defect present: invalid --status was accepted")
        return 1
    print("ok: invalid --status fails as CLI usage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
