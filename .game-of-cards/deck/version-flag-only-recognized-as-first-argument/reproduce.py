"""Reproduce: `goc --version` is only recognized as the first argument.

Runs the console script in a subprocess for several argv shapes and
checks that the version flag is honored regardless of position.

Before the fix:
  - `goc --version`            → prints version, exit 0   (passes)
  - `goc --no-color --version` → argparse error, exit 2   (FAILS)
  - `goc --status all --version` → argparse error, exit 2 (FAILS)
  - `--version` absent from `goc --help`                  (FAILS)

After the fix, all four shapes succeed. The script exits 0 only when
the defect is gone.
"""

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


def _run(args):
    """Invoke the CLI via `python -m goc.cli` from the repo root."""
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
    )


def main() -> int:
    failures = []

    # 1. --version as the first token (already works today)
    r = _run(["--version"])
    ok = r.returncode == 0 and "version" in r.stdout.lower()
    print(f"[{'PASS' if ok else 'FAIL'}] goc --version "
          f"→ exit {r.returncode}, stdout={r.stdout.strip()!r}")
    if not ok:
        failures.append("goc --version")

    # 2. --version after another global flag
    r = _run(["--no-color", "--version"])
    ok = r.returncode == 0 and "version" in r.stdout.lower()
    print(f"[{'PASS' if ok else 'FAIL'}] goc --no-color --version "
          f"→ exit {r.returncode}, stdout={r.stdout.strip()!r}, "
          f"stderr={r.stderr.strip()!r}")
    if not ok:
        failures.append("goc --no-color --version")

    # 3. --version after a status filter
    r = _run(["--status", "all", "--version"])
    ok = r.returncode == 0 and "version" in r.stdout.lower()
    print(f"[{'PASS' if ok else 'FAIL'}] goc --status all --version "
          f"→ exit {r.returncode}, stdout={r.stdout.strip()!r}, "
          f"stderr={r.stderr.strip()!r}")
    if not ok:
        failures.append("goc --status all --version")

    # 4. --version listed in --help
    r = _run(["--help"])
    ok = "--version" in r.stdout
    print(f"[{'PASS' if ok else 'FAIL'}] goc --help lists --version "
          f"→ {'present' if ok else 'absent'}")
    if not ok:
        failures.append("goc --help omits --version")

    if failures:
        print(f"\nDEFECT PRESENT — {len(failures)} shape(s) failed: {failures}")
        return 1
    print("\nAll version-flag shapes honored — defect fixed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
