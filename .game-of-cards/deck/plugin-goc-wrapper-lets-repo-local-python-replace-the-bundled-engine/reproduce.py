#!/usr/bin/env python3
"""The plugin `bin/goc` wrapper resolves `goc` from the working directory first.

Drops an impostor `goc/` package into a scratch cwd and runs the plugin wrapper
there. The bundled engine should win — the plugin's contract is that it ships
its own engine. Today the repo-local package does.

Exits 0 once the wrapper is immune to a cwd-local `goc/` package.
"""

from __future__ import annotations

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

IMPOSTOR_CLI = '''\
import sys
print("IMPOSTOR-ENGINE")
print("goc resolved from ->", sys.modules["goc"].__file__)
print("sys.path[:3] =", sys.path[:3])
'''


def main() -> int:
    failures = []
    for payload in ("claude-plugin", "codex-plugin"):
        wrapper = ROOT / payload / "bin" / "goc"
        if not wrapper.exists():
            print(f"[SKIP] no wrapper at {wrapper}")
            continue

        work = Path(tempfile.mkdtemp(prefix="goc-shadow-"))
        try:
            pkg = work / "goc"
            pkg.mkdir()
            (pkg / "__init__.py").write_text('__version__ = "IMPOSTOR"\n')
            (pkg / "cli.py").write_text(IMPOSTOR_CLI)

            proc = subprocess.run(
                [str(wrapper), "--version"], cwd=work,
                capture_output=True, text=True,
            )
            out = proc.stdout.strip()
            hijacked = "IMPOSTOR-ENGINE" in out
            print(f"\n[{payload}] hijacked={hijacked}")
            for line in out.splitlines():
                print(f"  {line}")
            if hijacked:
                failures.append(payload)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    if failures:
        print(f"\n[FAIL] repo-local goc/ replaces the bundled engine for: "
              f"{', '.join(failures)}")
        return 1
    print("\n[OK] the bundled engine wins over a cwd-local goc/ package.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
