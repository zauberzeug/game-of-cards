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

        create = _run(cwd, env, "new", "good-card", "--gate", "none", "--tag", "story")
        bad_new = _run(cwd, env, "new", "bug-123-regression", "--gate", "none", "--tag", "story")
        moved = _run(cwd, env, "move", "good-card", "bug-123-regression")
        validate = _run(cwd, env, "validate", "--quiet")

    print(f"create_good_exit={create.returncode}")
    print(f"new_bad_exit={bad_new.returncode}")
    print(f"new_bad_stderr_first={bad_new.stderr.splitlines()[0] if bad_new.stderr else ''}")
    print(f"move_bad_exit={moved.returncode}")
    print(f"move_bad_stdout={moved.stdout.strip()}")
    print(f"validate_exit={validate.returncode}")
    print(f"validate_stderr={validate.stderr.strip()}")

    if create.returncode != 0:
        return create.returncode
    if bad_new.returncode != 0 and moved.returncode == 0 and validate.returncode == 0:
        print("defect present: move accepts a title that new rejects")
        return 1
    print("ok: move enforces the same title guard as new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
