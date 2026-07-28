#!/usr/bin/env python3
"""Prove that `openclaw-plugin/dist/` can drift from `index.ts` unchecked.

The OpenClaw plugin's loadable artifact is the *committed* esbuild bundle
`openclaw-plugin/dist/index.js` (`package.json` sets both `main` and
`openclaw.extensions` to it). Every other generated tree in this repo has a
byte-for-byte tripwire. This script shows `dist/` has none: it edits
`index.ts` in place, re-runs the repo's entire guard set, observes that
everything stays green, and restores the file.

The mutation is wrapped in try/finally and restores the original bytes on
every exit path, so a clean checkout stays clean.

Run:  uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exits 0 while the defect is present (no guard catches the drift), 1 once a
guard lands.
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


ROOT = _repo_root()
TS = ROOT / "openclaw-plugin" / "index.ts"
DIST = ROOT / "openclaw-plugin" / "dist" / "index.js"
MARKER = "GOC_DIST_DRIFT_PROBE_MARKER"
ANCHOR = 'const TOOL_ONLY_VERBS = ["skill"] as const;'

# Prefer the project venv so the guards import the same `goc` CI uses.
VENV_PY = ROOT / ".venv" / "bin" / "python"
PY = str(VENV_PY) if VENV_PY.exists() else sys.executable

GUARDS: list[tuple[str, list[str]]] = [
    ("scripts/sync_plugin_assets.py --check",
     [PY, "scripts/sync_plugin_assets.py", "--check"]),
    ("scripts/port_skills_to_openclaw.py --check",
     [PY, "scripts/port_skills_to_openclaw.py", "--check"]),
    ("goc validate",
     [PY, "-m", "goc.cli", "validate", "--quiet"]),
    ("python -m unittest discover -s tests",
     [PY, "-m", "unittest", "discover", "-s", "tests"]),
]


def main() -> int:
    original = TS.read_text()
    dist_before = DIST.read_bytes()
    if ANCHOR not in original:
        print(f"SKIP: anchor line not found in {TS.relative_to(ROOT)}; "
              "update ANCHOR to any stable line in the file.")
        return 0

    print(f"artifact the OpenClaw runtime loads : "
          f"{DIST.relative_to(ROOT)} ({len(dist_before)} bytes)")
    print(f"source it is built from             : {TS.relative_to(ROOT)}")
    print()

    results: list[tuple[str, int]] = []
    try:
        TS.write_text(original.replace(ANCHOR, f"{ANCHOR}\nconst {MARKER} = 1;"))
        print(f"[mutate] appended `const {MARKER} = 1;` to index.ts, "
              "left dist/ untouched")
        print(f"  index.ts contains marker : {MARKER in TS.read_text()}")
        print(f"  dist/index.js has marker : {MARKER in DIST.read_text()}")
        print(f"  dist/index.js unchanged  : {DIST.read_bytes() == dist_before}")
        print()
        print("[guards] every drift check this repo runs, against the drifted tree:")
        for label, cmd in GUARDS:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            results.append((label, proc.returncode))
            verdict = "PASS (misses the drift)" if proc.returncode == 0 else "FAIL (catches it)"
            print(f"  exit={proc.returncode}  {label:<44} {verdict}")
    finally:
        TS.write_text(original)
        assert TS.read_text() == original, "failed to restore index.ts"

    print()
    print(f"restored {TS.relative_to(ROOT)} to its original bytes")
    missed = [label for label, code in results if code == 0]
    print()
    if len(missed) == len(GUARDS):
        print(f"DEFECT PRESENT: all {len(GUARDS)} guards pass on a tree whose "
              "compiled\n  dist/index.js no longer corresponds to index.ts. "
              "Nothing in pre-commit,\n  CI, or the regression suite compares "
              "the two.")
        return 0
    print(f"DEFECT FIXED: {len(GUARDS) - len(missed)} guard(s) caught the drift.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
