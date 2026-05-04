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

        for title in ("card-a", "card-b"):
            created = _run(cwd, env, "new", title, "--gate", "none", "--tag", "story")
            if created.returncode != 0:
                print(created.stdout)
                print(created.stderr)
                return created.returncode

        first = _run(cwd, env, "advance", "card-a", "--by", "card-b", "--no-commit")
        second = _run(cwd, env, "advance", "card-b", "--by", "card-a", "--no-commit")
        validate = _run(cwd, env, "validate", "--quiet")

    print(f"first_advance_exit={first.returncode}")
    print(f"first_advance_stdout={first.stdout.strip()}")
    print(f"second_advance_exit={second.returncode}")
    print(f"second_advance_stdout={second.stdout.strip()}")
    print(f"validate_exit={validate.returncode}")
    print(f"validate_stderr={validate.stderr.strip()}")

    if first.returncode == 0 and second.returncode == 0 and validate.returncode != 0:
        print("defect present: advance created a relation cycle that validate rejects")
        return 1
    print("ok: advance rejects cycle-creating edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
