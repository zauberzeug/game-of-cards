"""Reproduce: `goc --help` omits `install` and `upgrade` subcommands.

Exits non-zero on the unfixed tree (`install` / `upgrade` missing from
the subcommand choices line of `goc --help`). After the fix, both
asserts pass and exit code is zero.
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
    help_out = subprocess.run(
        ["uv", "run", "goc", "--help"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    ).stdout

    # Print the subcommands choices line for context.
    for line in help_out.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            print("goc --help subcommands line:")
            print(f"  {stripped}")
            break
    else:
        print("goc --help: no subcommand choices line found")

    install_ok = "install" in help_out
    upgrade_ok = "upgrade" in help_out
    print(f"\nASSERT install in --help output: {'PASS' if install_ok else 'FAIL'}")
    print(f"ASSERT upgrade in --help output: {'PASS' if upgrade_ok else 'FAIL'}")

    # Sanity check: the verbs DO exist; they are just hidden from --help.
    for verb in ("install", "upgrade"):
        r = subprocess.run(
            ["uv", "run", "goc", verb, "--help"],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        status = "OK" if r.returncode == 0 else f"FAIL ({r.returncode})"
        print(f"goc {verb} --help: {status} (verb exists, just hidden from --help)")

    return 0 if (install_ok and upgrade_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
