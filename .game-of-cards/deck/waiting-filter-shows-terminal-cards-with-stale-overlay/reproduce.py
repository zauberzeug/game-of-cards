"""Proof that `goc --waiting` lists terminal cards carrying a stale overlay.

`goc wait <card> --reason ...` sets the impediment overlay; closing the
card (`goc done` / `goc status ... disproved|superseded`) never clears it
— a documented invariant. The `--waiting` view is meant to surface
*active* impediments, yet its filter applies `waiting_impedes(t)` with no
terminal-status gate, so a closed card with a stale overlay shows up.

Run: `uv run python .game-of-cards/deck/<title>/reproduce.py`
Exits 0 when the defect is fixed (no terminal card in the impeded view),
non-zero while it fires.
"""
from __future__ import annotations

import json
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


def _write_card(cwd: Path, title: str, status: str, *, closed_at: str | None) -> None:
    card_dir = cwd / "deck" / title
    card_dir.mkdir(parents=True)
    closed = f'"{closed_at}"' if closed_at is not None else "null"
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-04\n"
        f"closed_at: {closed}\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "waiting_on: external\n"
        'waiting_until: "2099-12-31"\n'
        "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        _write_card(cwd, "closed-but-still-deferred", "done", closed_at="2026-05-10")
        _write_card(cwd, "open-impeded", "open", closed_at=None)

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--waiting", "--json"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            print("goc --waiting failed:", result.stderr, file=sys.stderr)
            return 2

        shown = [(c["title"], c["status"]) for c in json.loads(result.stdout)]
        print("Cards shown by `goc --waiting`:", shown)

        terminal = {"done", "disproved", "superseded"}
        leaked = [t for t, s in shown if s in terminal]
        if leaked:
            print("BUG CONFIRMED -- terminal cards in impeded view:", leaked)
            return 1
        print("OK -- impeded view shows only live cards:", [t for t, _ in shown])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
