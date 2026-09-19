#!/usr/bin/env python3
"""Standup Section 4 drops every card that was claimed before it was parked.

Runs the `## Section 4 — Waiting on you` command exactly as
`goc/templates/skills/standup/SKILL.md` ships it, against a fixture deck that
covers the whole (status x human_gate) grid the section claims to span. The
only edit is the one the test harness needs: `goc` is not on PATH here, so the
bare verb is rewritten to the in-tree module. Everything after it — the pipe,
the `python3 -c` filter, the gate predicate — runs verbatim.

Exits 1 while the defect fires, 0 once Section 4 reports every live gated card.
"""

from __future__ import annotations

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
sys.path.insert(0, str(ROOT))

SKILL = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"
TERMINAL_STATUSES = ("done", "disproved", "superseded")

# (title, status, human_gate, draft) -> should Section 4 list it?
FIXTURES = [
    ("open-decision", "open", "decision", False, True),
    ("open-session", "open", "session", False, True),
    ("active-decision", "active", "decision", False, True),
    ("active-session", "active", "session", False, True),
    ("active-ungated", "active", "none", False, False),
    ("open-ungated", "open", "none", False, False),
    ("done-stale-gate", "done", "decision", False, False),
    ("draft-decision", "open", "decision", True, False),
]


def section4_block() -> str:
    """The fenced command block under `## Section 4`, read from the template."""
    text = SKILL.read_text(encoding="utf-8")
    after = text.split("## Section 4", 1)
    if len(after) != 2:
        raise AssertionError("standup Section 4 heading not found in SKILL.md")
    fence = re.search(r"```bash\n(.*?)```", after[1], re.DOTALL)
    if not fence:
        raise AssertionError("standup Section 4 command fence not found in SKILL.md")
    return fence.group(1)


def block_command(block: str) -> str:
    """The shipped block, with the bare `goc` verb pointed at the in-tree engine."""
    return re.sub(r"(?m)^goc ", f"{sys.executable} -m goc.cli ", block, count=1)


def write_card(cwd: Path, title: str, status: str, gate: str, draft: bool) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    closed = '"2026-05-10T00:00:00Z"' if status in TERMINAL_STATUSES else "null"
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        'created: "2026-05-04T00:00:00Z"\n'
        f"closed_at: {closed}\n"
        f"human_gate: {gate}\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        + ("draft: true\n" if draft else "")
        + "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n",
        encoding="utf-8",
    )
    (card_dir / "log.md").write_text("", encoding="utf-8")


def main() -> int:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"

    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        for title, status, gate, draft, _ in FIXTURES:
            write_card(cwd, title, status, gate, draft)
        out = subprocess.run(
            block_command(section4_block()),
            shell=True,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        ).stdout

    reported = {line.split(" [", 1)[0] for line in out.splitlines() if " [" in line}

    print("standup Section 4 — 'Waiting on you' — over the (status x gate) grid")
    print()
    print(f"{'card':<18} {'status':<10} {'gate':<9} {'draft':<6} {'expected':<9} reported")
    print("-" * 70)
    misses = []
    for title, status, gate, draft, expected in FIXTURES:
        got = title in reported
        flag = "" if got == expected else "   <-- WRONG"
        if got != expected:
            misses.append(title)
        print(
            f"{title:<18} {status:<10} {gate:<9} {str(draft):<6} "
            f"{str(expected):<9} {got}{flag}"
        )

    print()
    if misses:
        print(f"DEFECT: {len(misses)} card(s) misreported: {', '.join(misses)}")
        print(
            "Section 4 queries `--status open`, so a card claimed BEFORE it was "
            "parked is dropped before the gate filter runs."
        )
        return 1
    print("OK: Section 4 spans every live status and excludes terminal + draft cards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
