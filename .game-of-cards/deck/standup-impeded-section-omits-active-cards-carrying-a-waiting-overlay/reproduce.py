"""Reproduce the standup Impeded section's status-scope drop.

`goc/templates/skills/standup/SKILL.md` feeds Section 2 ("Impeded
(waiting overlay)") from a Context block that queries
`goc --json --status open`. Section 2's own prose says:

    A card may appear here even while `status: active` — the overlay
    is orthogonal to the progress status.

`--status open` makes that impossible: `filter_cards` drops every
`active` card before the block's `waiting_on` filter ever runs.

The engine already settled this exact scope question for its own
impediment view — `deck/goc-waiting-default-status-hides-active-impeded-cards/`
(closed) made `--waiting` auto-extend the default status to `all`,
and `live_impeded` then re-narrows by excluding terminal-status and
draft cards. `goc --waiting --json` is therefore the engine's answer
to "which cards carry a live impediment overlay", across statuses.

This script builds a four-cell deck and compares the two:

  a-active-impeded  active, waiting_on  -> engine: impeded. Block MISSES it.
  b-open-impeded    open,   waiting_on  -> both agree: impeded.
  c-done-impeded    done,   waiting_on  -> engine: NOT impeded (terminal).
                                           Pins the second half of the fix:
                                           widening scope must not start
                                           reporting closed cards.
  d-clean           open,   no overlay  -> both agree: not impeded.

Exit status: 1 while the defect is present, 0 once the Context block
agrees with the engine on every cell.

Run from anywhere:
    uv run python .game-of-cards/deck/standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay/reproduce.py
"""

from __future__ import annotations

import json
import os
import re
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
SKILL = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"


def write_card(deck: Path, title: str, *, status: str, waiting_on: str | None) -> None:
    card = deck / title
    card.mkdir(parents=True)
    fm = [
        "---",
        f"title: {title}",
        f"summary: {title}",
        f"status: {status}",
        "stage: null",
        "contribution: low",
        'created: "2026-05-01T00:00:00Z"',
        'closed_at: "2026-05-02T00:00:00Z"' if status == "done" else "closed_at: null",
        "human_gate: none",
        "advances: []",
        "advanced_by: []",
        "tags: [bug]",
        "definition_of_done: |",
        "  - [x] x" if status == "done" else "  - [ ] x",
    ]
    if waiting_on is not None:
        fm.append(f"waiting_on: {waiting_on}")
    fm.append("---")
    (card / "README.md").write_text("\n".join(fm) + f"\n\n# {title}\n", encoding="utf-8")
    (card / "log.md").write_text("", encoding="utf-8")


def section2_context_block() -> str:
    """The live `!`-block that populates standup Section 2, read from the template.

    Read rather than restated so the check cannot silently pass against a
    stale copy of the query: this is the one line under test.
    """
    for line in SKILL.read_text(encoding="utf-8").splitlines():
        if line.startswith("!`") and "impeded" in line:
            return line
    raise RuntimeError("standup Section 2 Context block not found in SKILL.md")


def block_command(block: str) -> str:
    """Strip the `!`...`` wrapper and the bootstrap-vs-PATH preamble.

    The template's fallback arm (`else goc <args>; fi`) is the invocation
    used when no vendored bootstrap script is present, which is the shape
    this reproducer runs.
    """
    inner = block[2:].rstrip("`")
    inner = re.sub(r"^.*?;\s*else\s+goc\s+", "", inner, count=1)
    return "python3 -m goc.cli " + inner.replace("; fi", "", 1)


def run(cmd: str, cwd: Path, env: dict) -> str:
    r = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True)
    return r.stdout


def main() -> int:
    block = section2_context_block()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        write_card(deck, "a-active-impeded", status="active", waiting_on="external")
        write_card(deck, "b-open-impeded", status="open", waiting_on="external")
        write_card(deck, "c-done-impeded", status="done", waiting_on="external")
        write_card(deck, "d-clean", status="open", waiting_on=None)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)

        printed = run(block_command(block), cwd, env)
        skill_says = sorted(
            line.split(" [", 1)[0] for line in printed.splitlines() if " [waiting_on:" in line
        )

        engine_json = run(
            "python3 -m goc.cli --waiting --json", cwd, env
        )
        engine_says = sorted(c["title"] for c in json.loads(engine_json or "[]"))

    print("standup Section 2 Context block :", skill_says)
    print("engine `goc --waiting` (truth)  :", engine_says)
    print()
    missing = sorted(set(engine_says) - set(skill_says))
    extra = sorted(set(skill_says) - set(engine_says))
    print("engine impedes, standup omits  :", missing)
    print("standup reports, engine does not:", extra)
    print()
    if missing or extra:
        print("DEFECT PRESENT — standup Section 2 disagrees with the engine.")
        print(
            "Section 2 prose: 'A card may appear here even while `status: active`"
            " — the overlay is orthogonal to the progress status.'"
        )
        return 1
    print("OK — standup Section 2 agrees with the engine on every cell.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
