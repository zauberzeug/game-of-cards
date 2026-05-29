"""Reproduce the `goc --waiting` filter drift against `waiting_impedes`.

The `--waiting` filter at `goc/engine.py:2846` checks one overlay
field:

    filtered = [t for t in filtered if t.waiting_on is not None]

The engine's authoritative impedance predicate `waiting_impedes` at
`goc/engine.py:1752` evaluates a four-cell matrix over BOTH overlay
fields (`waiting_on` and `waiting_until`). The CLI flag disagrees
with the engine in two cells:

  1. `waiting_on` set with elapsed `waiting_until`  → engine: NOT
     impeded (the elapsed-wait resurfaces the card), but `--waiting`
     INCLUDES it.
  2. No `waiting_on`, future `waiting_until` (bare deferral) →
     engine: IMPEDED, but `--waiting` OMITS it.

Run from the repo root:
    uv run python .game-of-cards/deck/goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/reproduce.py
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
sys.path.insert(0, str(ROOT))


def write_card(deck_dir: Path, title: str, *, waiting_on: str | None, waiting_until: str | None) -> None:
    card_dir = deck_dir / title
    card_dir.mkdir(parents=True)
    fm = [
        "---",
        f"title: {title}",
        f"summary: {title}",
        "status: open",
        "stage: null",
        "contribution: low",
        "created: 2026-05-01",
        "closed_at: null",
        "human_gate: none",
        "advances: []",
        "advanced_by: []",
        "tags: [bug]",
        "definition_of_done: |",
        "  - [ ] x",
    ]
    if waiting_on is not None:
        fm.append(f"waiting_on: {waiting_on}")
    if waiting_until is not None:
        fm.append(f'waiting_until: "{waiting_until}"')
    fm.append("---")
    (card_dir / "README.md").write_text("\n".join(fm) + f"\n\n# {title}\n")
    (card_dir / "log.md").write_text("")


def run_goc(args: list[str], cwd: Path) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        print(f"goc {' '.join(args)} failed:", result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout


def titles_in_table(out: str) -> set[str]:
    """Return the title column of a `goc` table render."""
    titles: set[str] = set()
    for line in out.splitlines():
        line = line.rstrip()
        if not line or line.startswith(("ACTIVE:", "TITLE", "-")):
            continue
        # Title is the first whitespace-delimited token; valid card
        # titles never contain spaces.
        token = line.split(None, 1)[0]
        if token:
            titles.add(token)
    return titles


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck_dir = cwd / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)

        # Cell A: waiting_on set, elapsed waiting_until -> engine NOT impeded
        write_card(deck_dir, "a-elapsed-with-reason", waiting_on="external", waiting_until="2024-01-01")
        # Cell B: no waiting_on, future waiting_until -> engine IMPEDED
        write_card(deck_dir, "b-future-bare-deferral", waiting_on=None, waiting_until="2030-01-01")
        # Cell C: waiting_on set, no waiting_until -> both agree (impeded)
        write_card(deck_dir, "c-reason-only", waiting_on="external", waiting_until=None)
        # Cell D: no overlay -> both agree (not impeded)
        write_card(deck_dir, "d-clean", waiting_on=None, waiting_until=None)

        # CLI says:
        waiting_out = run_goc(["--waiting", "--no-color"], cwd)
        cli_says = titles_in_table(waiting_out)

        # Engine ground truth from JSON: a card is impeded iff
        # `waiting_impedes` returns True. The JSON exposes `ready`
        # (= card_is_ready, which is False iff impeded OR gated OR
        # non-open) plus the overlay fields, so reconstruct
        # waiting_impedes by intersecting "not ready" with
        # "overlay set" (since all test cards are open, gate none).
        json_out = run_goc(["--json", "--status", "open"], cwd)
        cards = json.loads(json_out)
        engine_says = {
            c["title"] for c in cards
            if not c["ready"]
            and c.get("human_gate") == "none"
            and (c.get("waiting_on") is not None or c.get("waiting_until") is not None)
        }

    print("goc --waiting             :", sorted(cli_says))
    print("waiting_impedes ground truth:", sorted(engine_says))
    print()

    only_cli = sorted(cli_says - engine_says)
    only_engine = sorted(engine_says - cli_says)
    print("false-positive (--waiting includes, engine has resurfaced):", only_cli)
    print("false-negative (engine impedes, --waiting omits)         :", only_engine)

    expected_fp = ["a-elapsed-with-reason"]
    expected_fn = ["b-future-bare-deferral"]
    drift_as_predicted = (only_cli, only_engine) == (expected_fp, expected_fn)
    print()
    print("DRIFT REPRODUCED" if drift_as_predicted else "(unexpected — investigate)")
    return 0 if drift_as_predicted else 1


if __name__ == "__main__":
    sys.exit(main())
