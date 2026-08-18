"""`goc --board --json` prints an ASCII table and exits 0 instead of refusing.

`--board` and `--json` are two renderers for the same query. `_cmd_default`
picks between them with a bare `if args.board: ... elif args.as_json: ...`
chain, so `--board` silently wins and `--json` never runs — no error, no
warning, exit 0, and stdout that no JSON parser accepts.

Every other conflicting-flag pair reachable from the same function refuses
with exit 2. This script asserts the contract three ways:

1. `--json` alone parses as JSON (control).
2. `--board --json` (and the reverse order) still parses as JSON — FAILS today.
3. The neighbouring `--done --status open` conflict exits 2 — the in-repo
   precedent this card holds `--board --json` to.

Exits 0 once the defect no longer fires.
"""

from __future__ import annotations

import json
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

CARD = """\
---
title: probe-card
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# probe-card

Fixture.
"""


def _goc(deck_root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=deck_root,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT), "GOC_WORKER": ""},
    )


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        card = root / ".game-of-cards" / "deck" / "probe-card"
        card.mkdir(parents=True)
        (card / "README.md").write_text(CARD, encoding="utf-8")
        (card / "log.md").write_text("", encoding="utf-8")

        cases = [
            ("--json alone emits JSON", ["--status", "all", "--json"], True),
            ("--board --json emits JSON or refuses", ["--status", "all", "--board", "--json"], False),
            ("--json --board emits JSON or refuses", ["--status", "all", "--json", "--board"], False),
        ]
        for label, argv, control in cases:
            proc = _goc(root, *argv)
            ok = _is_json(proc.stdout)
            # A refusal is also an acceptable fix for the conflicting pair:
            # exit 2 with a diagnostic is what the neighbouring conflicts do.
            refused = proc.returncode == 2 and "error" in proc.stderr.lower()
            passed = ok if control else (ok or refused)
            if passed:
                print(f"PASS  {label} (exit={proc.returncode})")
            else:
                failures += 1
                first = proc.stdout.splitlines()[0][:60] if proc.stdout else "<empty>"
                print(
                    f"FAIL  BUG: {label} — exit={proc.returncode}, "
                    f"stderr={proc.stderr.strip()!r}, stdout[0]={first!r}"
                )

        precedent = _goc(root, "--done", "--status", "open")
        if precedent.returncode == 2:
            print(
                f"PASS  precedent: --done --status refuses "
                f"(exit={precedent.returncode}: {precedent.stderr.strip()})"
            )
        else:
            failures += 1
            print(f"FAIL  precedent: --done --status exited {precedent.returncode}")

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
