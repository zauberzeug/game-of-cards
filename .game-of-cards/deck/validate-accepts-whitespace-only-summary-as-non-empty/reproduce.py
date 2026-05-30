"""Reproduce: `goc validate` accepts `summary: "   "` (whitespace-only).

A card with a whitespace-only `summary` field passes `goc validate` with
exit 0, even though `goc quality-pass` treats the same shape as a
"Missing summary" quality issue. The two surfaces disagree.

Mirrors the gap the recently-closed worker cards
(`validate-accepts-whitespace-only-worker-as-non-empty`,
`validate-accepts-whitespace-only-worker-where-as-non-empty`) fixed for
the `worker` field.
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


ROOT = _repo_root()


def _write_card(cwd: Path, title: str, summary_line: str) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"{summary_line}\n"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-30\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] PROCESS: test card\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card_dir / "log.md").write_text("")


def _run_validate(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "ws-summary", 'summary: "   "')
        result = _run_validate(cwd)

        print(f"# `goc validate` with summary: \"   \"")
        print(f"exit_code: {result.returncode}")
        print(f"stdout:\n{result.stdout}")
        print(f"stderr:\n{result.stderr}")

        if result.returncode == 0:
            print("DEFECT CONFIRMED: validate accepted whitespace-only summary "
                  "(should reject with same message shape as the worker fix).")
            return 0
        if "summary" in (result.stderr + result.stdout).lower():
            print("FIX DETECTED: validate now rejects whitespace-only summary.")
            return 1
        print("UNEXPECTED: validate failed for some other reason.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
