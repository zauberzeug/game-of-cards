"""Reproduce: `goc status <X> superseded --by <Y>` accepts a terminal-status <Y>.

Runs the goc CLI against a throwaway deck directory and exercises the
three terminal statuses (`done`, `disproved`, `superseded`) as the
successor. Each case currently succeeds (defect fires); after the fix,
each must exit non-zero with an error mentioning the terminal status.

Exit code 0 means the script ran cleanly — the BEFORE/AFTER verdict
must be read from the printed table.
"""

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


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))


def _write_card(deck_dir: Path, title: str, status: str = "open") -> None:
    card_dir = deck_dir / title
    card_dir.mkdir(parents=True, exist_ok=True)
    (card_dir / "README.md").write_text(
        f"""---
title: {title}
summary: ""
status: {status}
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: placeholder
---

# {title}

Placeholder.
"""
    )
    (card_dir / "log.md").write_text("")


def _run_goc(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        scratch = Path(tmpdir)
        deck_dir = scratch / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        # Mark this as a goc project root.
        (scratch / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        # Seed three terminal-status successors and three live origins.
        for term in ("done", "disproved", "superseded"):
            _write_card(deck_dir, f"successor-{term}", status=term)
            _write_card(deck_dir, f"origin-for-{term}", status="open")

        rows: list[tuple[str, int, str]] = []
        for term in ("done", "disproved", "superseded"):
            origin = f"origin-for-{term}"
            successor = f"successor-{term}"
            # `goc status <origin> superseded --by <successor>` should be rejected
            # whenever the successor is terminal — but currently is accepted for
            # done and disproved, and the superseded case is caught only by an
            # unrelated cycle / "must be live" semantic that does not exist.
            result = _run_goc(
                [
                    "status",
                    origin,
                    "superseded",
                    "--by",
                    successor,
                    "--no-commit",
                ],
                cwd=scratch,
                env=env,
            )
            stderr_tail = (result.stderr or "").strip().splitlines()
            tail = stderr_tail[-1] if stderr_tail else "(no stderr)"
            rows.append((term, result.returncode, tail))

        print(f"{'SUCCESSOR.STATUS':<20} {'EXITCODE':<10} STDERR TAIL")
        print("-" * 80)
        for term, code, tail in rows:
            print(f"{term:<20} {code:<10} {tail}")

        print()
        print("Interpretation:")
        print("  BEFORE fix — every row exits 0 (defect fires; dead-end link written).")
        print("  AFTER  fix — every row exits non-zero with an error mentioning")
        print("               the terminal status; no supersession transition occurs.")

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
