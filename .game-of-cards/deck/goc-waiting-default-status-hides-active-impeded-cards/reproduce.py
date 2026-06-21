"""Reproduce: `goc --waiting` (default status) hides active impeded cards.

An `active` card carrying a `waiting_on` overlay is genuinely impeded
(the three-axis stuck model: a card may be `status: active` AND carry
`waiting_on`). The impediment view `goc --waiting` should surface it.
But `_cmd_default` defaults the status filter to `open` (only extending
to `all` for `--closed-since`), so the active card is dropped before the
`--waiting` filter runs.

Exits 0 when the defect is fixed (active impeded card appears in
`goc --waiting`), non-zero while the defect is present.
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


def _write_card(deck: Path, title: str, status: str) -> None:
    d = deck / title
    d.mkdir(parents=True)
    (d / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-04\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "waiting_on: external\n"
        "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        _write_card(deck, "open-impeded", "open")
        _write_card(deck, "active-impeded", "active")

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
        # Use --json so the human-facing ACTIVE notice (which itself names
        # the active card) cannot spuriously satisfy a substring check.
        titles = {c["title"] for c in json.loads(result.stdout)}
        print("--- goc --waiting (default status), titles ---")
        print(sorted(titles))

        open_shown = "open-impeded" in titles
        active_shown = "active-impeded" in titles

        print(f"open-impeded surfaced:   {open_shown}")
        print(f"active-impeded surfaced: {active_shown}")

        if open_shown and active_shown:
            print("\nPASS: both impeded cards surface in `goc --waiting`.")
            return 0
        print(
            "\nFAIL: active impeded card is hidden from `goc --waiting` "
            "because the default status filter is `open`."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
