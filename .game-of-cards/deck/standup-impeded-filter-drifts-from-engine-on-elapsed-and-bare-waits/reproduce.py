"""Reproduce the standup-skill impeded-filter drift.

The standup skill's Context block filters impeded cards with
`[c for c in cards if c.get('waiting_on')]`. The engine predicate
`waiting_impedes` evaluates a four-cell matrix over `waiting_on` x
`waiting_until`, so the skill drifts from the engine in two cells:

  1. `waiting_on` set with elapsed `waiting_until`  → engine: NOT impeded
     (the elapsed-wait resurfaces the card; engine has re-added it to
     the pull queue), but the skill still lists it under "Impeded".
  2. No `waiting_on`, future `waiting_until` (bare deferral) → engine:
     IMPEDED (a future date implies a `deferred` wait), but the skill
     OMITS it from "Impeded".

The standup section header advertises a `waiting_on` overlay, but
the engine treats bare-`waiting_until` as a deferred wait too, and
the section text in the skill body promises a daily view of "what's
stuck" — drifting from `card_is_ready` makes the standup view lie
about both directions.

Run from the repo root:
    python3 .game-of-cards/deck/standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/reproduce.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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


def standup_impeded_filter(cards: list[dict]) -> list[str]:
    """The filter the standup skill applies (verbatim from SKILL.md line 18)."""
    return [c["title"] for c in cards if c.get("waiting_on")]


def engine_impeded(cards: list[dict]) -> list[str]:
    """What the engine considers impeded — i.e., not-ready due to overlay."""
    return [c["title"] for c in cards if not c["ready"] and c.get("human_gate") == "none"]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck_dir = cwd / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)

        # Cell 1: waiting_on set, elapsed waiting_until -> engine NOT impeded
        write_card(deck_dir, "a-elapsed-with-reason", waiting_on="external", waiting_until="2024-01-01")
        # Cell 2: no waiting_on, future waiting_until -> engine IMPEDED
        write_card(deck_dir, "b-future-bare-deferral", waiting_on=None, waiting_until="2030-01-01")
        # Sanity: waiting_on set with no waiting_until -> both agree (impeded)
        write_card(deck_dir, "c-reason-only", waiting_on="external", waiting_until=None)
        # Sanity: no overlay -> both agree (not impeded)
        write_card(deck_dir, "d-clean", waiting_on=None, waiting_until=None)

        import json
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--json", "--status", "open"],
            cwd=cwd, env=env, capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            print("goc --json failed:", result.stderr, file=sys.stderr)
            return 1
        cards = json.loads(result.stdout)
        cards.sort(key=lambda c: c["title"])

    skill_says = standup_impeded_filter(cards)
    engine_says = engine_impeded(cards)

    print("standup-skill impeded filter      :", skill_says)
    print("engine waiting_impedes / not-ready:", engine_says)
    print()

    only_skill = sorted(set(skill_says) - set(engine_says))
    only_engine = sorted(set(engine_says) - set(skill_says))
    print("false-positive (skill says impeded, engine has resurfaced):", only_skill)
    print("false-negative (engine impedes, skill omits)              :", only_engine)

    expected_fp = ["a-elapsed-with-reason"]
    expected_fn = ["b-future-bare-deferral"]
    drift = (only_skill, only_engine) != (expected_fp, expected_fn)
    print()
    print("DRIFT REPRODUCED" if not drift else "(unexpected — investigate)")
    return 0 if not drift else 1


if __name__ == "__main__":
    sys.exit(main())
