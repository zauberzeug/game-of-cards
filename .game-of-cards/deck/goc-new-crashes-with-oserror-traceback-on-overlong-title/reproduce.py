"""Reproduce: goc new crashes with a raw OSError traceback on an overlong title.

Runs `goc new <300 x 'a'>` in a scratch deck. Contract: bad input gets a
clean `ERROR:` line on stderr and exit 2. Observed today: an uncaught
`OSError: [Errno 36] File name too long` pathlib traceback.

Exits non-zero while the defect is present; exits zero once the CLI
rejects the title cleanly.
"""

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


ROOT = _repo_root()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        subprocess.run(["git", "init", "-q", str(scratch)], check=True)
        (scratch / ".game-of-cards" / "deck").mkdir(parents=True)
        proc = subprocess.run(
            [sys.executable, "-m", "goc.cli", "new", "a" * 300],
            cwd=scratch,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )
    print(f"exit code: {proc.returncode}")
    tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "(no stderr)"
    print(f"stderr tail: {tail}")
    if "Traceback" in proc.stderr or "OSError" in proc.stderr:
        print(
            "[FAIL] goc new leaked a raw OSError traceback instead of a "
            "clean `ERROR:` + exit 2 for an overlong title."
        )
        return 1
    if proc.returncode == 2 and "ERROR:" in proc.stderr:
        print("[OK] overlong title rejected cleanly (ERROR: line, exit 2).")
        return 0
    print(f"[FAIL] unexpected behavior: exit {proc.returncode}, no ERROR: line.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
