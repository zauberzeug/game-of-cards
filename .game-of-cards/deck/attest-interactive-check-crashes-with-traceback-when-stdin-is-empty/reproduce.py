#!/usr/bin/env python3
"""Reproduce: `goc attest` crashes with an EOFError traceback when an
interactive (`manual` / `agent`) closure check is reached and stdin is empty.

Builds a throwaway repo with one card and a `manual` layer-2 check, then runs
`goc attest` three ways:

  1. stdin at EOF (what an agent harness gives it) -> EXPECTED: declined
  2. stdin piped an answer                         -> already works today
  3. --non-interactive                             -> already works today

Case 1 is the defect: it dies with an unhandled EOFError instead of the
"declined" outcome case 3 already defines.

Exits 0 once case 1 no longer raises EOFError; exits 1 while the defect fires.
"""

from __future__ import annotations

import os
import shutil
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

CONFIG = """\
layer_2_project_dod:
  - name: docs-updated
    kind: manual
    description: Docs reflect the change
    prompt: "Docs updated? (y/n)"
layer_3_goc_dod:
  - name: dod-100-percent
    kind: derived
"""


def _goc(cwd: Path, *args: str, stdin_data: str | None = None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env.pop("GOC_WORKER", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd),
        env=env,
        input=stdin_data if stdin_data is not None else "",
        capture_output=True,
        text=True,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-attest-eof-"))
    try:
        subprocess.run(["git", "init", "-q", "."], cwd=str(tmp), check=True)
        subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=str(tmp), check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp), check=True)
        _goc(tmp, "install", "--claude")
        _goc(tmp, "new", "probe-card", "--summary", "A probe card.",
             "--contribution", "medium", "--gate", "none")
        (tmp / ".game-of-cards" / "config.yaml").write_text(CONFIG)

        print("=== case 1: stdin at EOF (agent harness) ===")
        eof = _goc(tmp, "attest", "probe-card")
        crashed = "EOFError" in eof.stderr
        print(f"exit={eof.returncode}  EOFError in stderr: {crashed}")
        print("stderr tail:", (eof.stderr.strip().splitlines() or [""])[-1])

        print("\n=== case 2: stdin piped 'y' (works today) ===")
        piped = _goc(tmp, "attest", "probe-card", stdin_data="y\n")
        print(f"exit={piped.returncode}  docs-updated line:",
              next((ln.strip() for ln in piped.stdout.splitlines()
                    if "docs-updated" in ln), "<none>"))

        print("\n=== case 3: --non-interactive (works today) ===")
        ni = _goc(tmp, "attest", "probe-card", "--non-interactive")
        print(f"exit={ni.returncode}  docs-updated line:",
              next((ln.strip() for ln in ni.stdout.splitlines()
                    if "docs-updated" in ln), "<none>"))

        print()
        if crashed:
            print("DEFECT: case 1 died with an unhandled EOFError traceback.")
            print("Expected: the same declined outcome case 3 already produces.")
            return 1
        print("FIXED: case 1 no longer raises EOFError.")
        declined = next((ln.strip() for ln in eof.stdout.splitlines()
                         if "docs-updated" in ln), "<none>")
        print(f"case 1 docs-updated line: {declined}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
