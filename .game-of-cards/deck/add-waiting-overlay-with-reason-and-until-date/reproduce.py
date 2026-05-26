"""Demonstrate the impediment overlay's read-time guard.

A card with a `waiting_until` in the future is hidden from `--ready`
output (the pull-card / next-card queue). When the date is in the past
the card RE-ENTERS the queue with no manual action, and the elapsed
wait is surfaced by `goc validate` as a `WAITING_OVERDUE` warning.

Run from the repo root:

    uv run python .game-of-cards/deck/add-waiting-overlay-with-reason-and-until-date/reproduce.py
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


def _card(title: str, *, waiting_on: str | None = None, waiting_until: str | None = None) -> str:
    lines = [
        "---",
        f"title: {title}",
        f"summary: Demo card for overlay reproduction ({title}).",
        "status: open",
        "stage: null",
        "contribution: medium",
        "created: 2026-05-01",
        "closed_at: null",
        "human_gate: none",
        "advances: []",
        "advanced_by: []",
        "tags: [bug]",
    ]
    if waiting_on is not None:
        lines.append(f"waiting_on: {waiting_on}")
    if waiting_until is not None:
        lines.append(f"waiting_until: {waiting_until}")
    lines += [
        "definition_of_done: |",
        "  - [ ] stub",
        "---",
        "",
        f"# {title}",
    ]
    return "\n".join(lines) + "\n"


def _write(deck: Path, name: str, body: str) -> None:
    d = deck / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "log.md").write_text("")
    (d / "README.md").write_text(body)


def _ready_titles(cwd: Path, env: dict) -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--ready", "--json"],
        cwd=cwd, env=env, text=True, capture_output=True, check=True,
    )
    return [d["title"] for d in json.loads(result.stdout)]


def _validate_warnings(cwd: Path, env: dict) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    return result.stderr


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        # 1. baseline: plain card with no overlay is ready.
        _write(deck, "plain", _card("plain"))
        # 2. future date hides the card from the ready queue.
        _write(deck, "future-defer", _card("future-defer", waiting_until="2099-01-01"))
        # 3. open-ended wait (reason set, no date) also hides.
        _write(deck, "external-wait", _card("external-wait", waiting_on="external"))

        ready = set(_ready_titles(cwd, env))
        print(f"step 1: ready (future date + reason set) = {sorted(ready)}")
        if "plain" not in ready:
            print("defect: plain card was unexpectedly hidden")
            return 1
        if "future-defer" in ready:
            print("defect: future waiting_until did not hide the card from the queue")
            return 1
        if "external-wait" in ready:
            print("defect: open-ended waiting_on did not hide the card from the queue")
            return 1

        # 4. elapsed date resurfaces the card and triggers WAITING_OVERDUE.
        _write(deck, "future-defer", _card("future-defer", waiting_until="2001-01-01"))
        ready = set(_ready_titles(cwd, env))
        print(f"step 2: ready (after backdating future-defer to 2001-01-01) = {sorted(ready)}")
        if "future-defer" not in ready:
            print("defect: elapsed waiting_until did not resurface the card")
            return 1

        warnings = _validate_warnings(cwd, env)
        print(f"step 3: validate warnings (truncated):\n{warnings.strip()[:400]}")
        if "WAITING_OVERDUE" not in warnings or "future-defer" not in warnings:
            print("defect: validate did not surface the elapsed wait as WAITING_OVERDUE")
            return 1

    print("ok: future date hides; elapsed date resurfaces and surfaces SLE escalation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
