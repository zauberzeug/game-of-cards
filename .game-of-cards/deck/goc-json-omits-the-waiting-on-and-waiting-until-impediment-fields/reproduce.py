"""Reproduce: `goc --json` (render_json) omits the impediment-overlay fields.

A card's readiness has three axes: status, human_gate, and the stored
impediment overlay (waiting_on / waiting_until). render_json emits the
first two axes plus the derived `ready` flag and the dependency axis
(`awaiting` / `dependency_awaiting`), but drops the raw overlay fields.
A JSON consumer can therefore see `ready: false` but cannot tell whether
the cause is the gate, a dependency, or an impediment overlay — and
cannot read the overlay's reason or expected-clear date.

Prints PASS (defect absent) or FAIL (defect present) and exits non-zero
while the defect is present.
"""

import json
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD = """\
---
title: impeded-card
summary: "A card carrying an active impediment overlay."
status: open
stage: null
contribution: medium
created: "2026-05-27T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
waiting_on: external
waiting_until: "2099-01-01"
definition_of_done: |
  - [ ] placeholder
---

# impeded card
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        card_dir = Path(tmp) / "impeded-card"
        card_dir.mkdir()
        (card_dir / "README.md").write_text(CARD)
        card = engine.load_card(card_dir)
        assert card is not None

        # Sanity: the engine reads the overlay off the card object.
        print(f"card.waiting_on    = {card.waiting_on!r}")
        print(f"card.waiting_until = {card.waiting_until!r}")
        print(f"card_is_ready      = {engine.card_is_ready(card, {card.title: card})}")

        record = json.loads(engine.render_json([card]))[0]
        keys = sorted(record.keys())
        print()
        print("render_json keys:")
        for k in keys:
            print(f"  {k}")
        print()

        has_waiting_on = "waiting_on" in record
        has_waiting_until = "waiting_until" in record
        print(f"'waiting_on' present in JSON?    {has_waiting_on}")
        print(f"'waiting_until' present in JSON? {has_waiting_until}")
        print(f"'human_gate' present in JSON?    {'human_gate' in record}")
        print(f"'ready' present in JSON?         {'ready' in record}")
        print(f"'awaiting' present in JSON?      {'awaiting' in record}")

        if has_waiting_on and has_waiting_until:
            print("\nPASS: impediment-overlay fields are exposed in the JSON record.")
            return 0
        print(
            "\nFAIL: JSON exposes the gate + dependency + ready axes but DROPS the "
            "impediment overlay (waiting_on / waiting_until). A consumer sees "
            "ready=false with no way to read the overlay reason or clear-date."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
