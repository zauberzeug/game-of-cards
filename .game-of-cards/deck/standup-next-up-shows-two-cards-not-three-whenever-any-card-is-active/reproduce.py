"""Standup Section 5 promises three ready cards; `head -5` delivers two
whenever any card is active.

Builds two hermetic scratch decks that differ in exactly one bit — whether
a single card carries `status: active` — and runs the Section 5 command
extracted verbatim from the shipped SKILL.md against each.

Exit 0 when both decks yield the promised 3 rows; exit 1 otherwise.
"""
import re
import shutil
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
PROMISED_ROWS = 3

CARD = """---
title: {title}
summary: probe card {title}
status: {status}
stage: null
contribution: high
created: "2026-09-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [ ] MECHANICAL: something concrete happens.
{extra}---

# {title}

Real body text so the card is not an unauthored scaffold.
"""


def section5_command() -> str:
    """Extract the Section 5 bash block from the shipped template."""
    text = SKILL.read_text()
    body = text.split("## Section 5 — Next up", 1)[1]
    block = re.search(r"```bash\n(.*?)```", body, re.S).group(1).strip()
    return block


def build_deck(root: Path, *, with_active: bool) -> None:
    deck = root / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    for name in ("alpha", "bravo", "charlie", "delta", "echo"):
        d = deck / f"ready-{name}"
        d.mkdir()
        (d / "README.md").write_text(
            CARD.format(title=f"ready-{name}", status="open", extra="")
        )
    if with_active:
        d = deck / "in-flight-card"
        d.mkdir()
        (d / "README.md").write_text(
            CARD.format(
                title="in-flight-card",
                status="active",
                extra='worker: {who: someone, where: main}\n',
            )
        )


def run(root: Path, command: str) -> str:
    return subprocess.run(
        ["sh", "-c", command],
        cwd=root,
        capture_output=True,
        text=True,
        env={"PATH": f"{ROOT / '.venv' / 'bin'}:/usr/bin:/bin", "HOME": str(root)},
    ).stdout


def rows(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("ready-")]


def main() -> int:
    command = section5_command()
    print("Section 5 command, verbatim from the shipped template:")
    print(f"    {command}\n")
    print("Prose contract (Section 5): "
          '"Show the top 3 open `human_gate: none` cards by value score"\n')

    failures = []
    for label, with_active in (("no active card", False), ("one active card", True)):
        tmp = Path(tempfile.mkdtemp())
        try:
            build_deck(tmp, with_active=with_active)
            out = run(tmp, command)
            got = rows(out)
            verdict = "OK " if len(got) == PROMISED_ROWS else "FAIL"
            print(f"[{verdict}] deck with {label}: "
                  f"{len(got)} of {PROMISED_ROWS} promised rows")
            for ln in out.splitlines():
                print(f"         | {ln}")
            print()
            if len(got) != PROMISED_ROWS:
                failures.append(label)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"DEFECT: Section 5 under-delivers with {', '.join(failures)}.")
        print("Cause: the engine writes a conditional one-line `ACTIVE:` banner to")
        print("stdout whenever a card is claimed outside the open queue, so the")
        print("fixed `head -5` budget spends three lines on chrome instead of two.")
        return 1
    print("Section 5 delivers the promised row count in both decks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
