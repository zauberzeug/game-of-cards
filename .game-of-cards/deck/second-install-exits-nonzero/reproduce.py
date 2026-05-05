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


def _run(cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        first = _run(cwd, env, "install", "--agents", "codex")
        second = _run(cwd, env, "install", "--agents", "codex")

    print(f"first_exit={first.returncode}")
    print(f"second_exit={second.returncode}")
    print(f"second_stdout={second.stdout.strip()}")
    print(f"second_stderr={second.stderr.strip()}")
    if first.returncode != 0:
        print("setup failed")
        return first.returncode
    if second.returncode != 0:
        print("defect present: second goc install exits non-zero")
        return 1
    print("ok: second goc install is a clean no-op")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
