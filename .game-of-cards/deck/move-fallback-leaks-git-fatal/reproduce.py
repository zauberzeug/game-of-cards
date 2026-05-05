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
        create = _run(cwd, env, "new", "source-card", "--gate", "none", "--tag", "story")
        moved = _run(cwd, env, "move", "source-card", "renamed-card")
        renamed_exists = (cwd / ".game-of-cards" / "deck" / "renamed-card" / "README.md").is_file()

    print(f"create_exit={create.returncode}")
    print(f"move_exit={moved.returncode}")
    print(f"move_stdout={moved.stdout.strip()}")
    print(f"move_stderr={moved.stderr.strip()}")
    print(f"renamed_exists={renamed_exists}")

    if create.returncode != 0:
        return create.returncode
    if moved.returncode == 0 and renamed_exists and "fatal: not a git repository" in moved.stderr:
        print("defect present: successful non-git move leaks git fatal stderr")
        return 1
    print("ok: non-git move fallback succeeds without fatal stderr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
