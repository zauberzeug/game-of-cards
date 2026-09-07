#!/usr/bin/env python3
"""Reproduce: skill `!`-blocks bound engine output with a fixed `head -N`.

Two failure modes, one root cause:

  A. `--status active -v | head -20` (pull-card, next-card) drops whole
     rows off the soft-lock table the skill body then tells the agent to
     "treat as a soft lock". No indicator marks the loss.
  B. `--json | head -N` (standup, refine-deck, retrospective) cuts a JSON
     document mid-object. The result is a syntax error, not a short list.

Runs the real CLI against this repo's own deck, applies each block's own
pipe, and reports what the agent actually receives. Exits non-zero while
the defect fires.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

# The six live `!`-blocks, read off goc/templates/skills/<skill>/SKILL.md.
# (skill, source line, goc args, head cap, kind)
BLOCKS = [
    ("pull-card", 30, ["--status", "active", "-v"], 20, "table"),
    ("pull-card", 42, ["--ready", "-v"], 22, "table"),
    ("next-card", 17, ["--status", "active", "-v"], 20, "table"),
    ("standup", 24, ["--status", "open", "--json"], 60, "json"),
    ("refine-deck", 91, ["--status", "open", "--json"], 100, "json"),
    ("retrospective", 17, ["--closed-since", "90d", "--json"], 100, "json"),
]


def goc(args: list[str]) -> str:
    """Run the engine the way the `!`-blocks do, from the repo root."""
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    # The blocks all use `2>&1`, so stderr is part of what the agent sees.
    return proc.stdout + proc.stderr


def card_titles(table: str, known: set[str]) -> set[str]:
    """Titles from a `-v` table: column 0 of every non-indented data row.

    Checked against the real deck directory names — under `-v` a long
    `summary:` wraps onto unindented continuation lines whose first word
    also matches the slug pattern, so the pattern alone over-counts.
    """
    titles = set()
    for line in table.splitlines():
        if not line or line.startswith((" ", "-", "TITLE", "ACTIVE:", "No cards")):
            continue
        head = line.split()[0]
        if head in known and re.fullmatch(r"[a-z0-9][a-z0-9-]*[a-z0-9]", head):
            titles.add(head)
    return titles


def main() -> int:
    failures = []
    known = {d.name for d in (ROOT / ".game-of-cards" / "deck").iterdir() if d.is_dir()}

    print("=== Verifying the `head -N` caps are still what the skills ship ===")
    for skill, lineno, args, cap, _kind in BLOCKS:
        src = (ROOT / "goc" / "templates" / "skills" / skill / "SKILL.md").read_text()
        line = src.splitlines()[lineno - 1]
        ok = f"head -{cap}" in line and all(a in line for a in args)
        print(f"  {'OK  ' if ok else 'DRIFT'} {skill}/SKILL.md:{lineno}  head -{cap}  {' '.join(args)}")
        if not ok:
            failures.append(f"{skill}:{lineno}: block drifted; update BLOCKS in this reproduce.py")

    for skill, lineno, args, cap, kind in BLOCKS:
        print(f"\n=== {skill}/SKILL.md:{lineno} — goc {' '.join(args)} | head -{cap} ===")
        full = goc(args)
        piped = "\n".join(full.splitlines()[:cap])
        total = len(full.splitlines())
        print(f"  engine emitted {total} lines; the block forwards {min(total, cap)}")

        if kind == "table":
            shown, kept = card_titles(full, known), card_titles(piped, known)
            lost = shown - kept
            print(f"  cards in full output: {len(shown)}; after head: {len(kept)}")
            if lost:
                print(f"  DEFECT: {len(lost)} card(s) vanished with no indicator:")
                for t in sorted(lost):
                    print(f"    - {t}")
                failures.append(
                    f"{skill}:{lineno}: head -{cap} hid {len(lost)} card(s) "
                    f"from a table the skill body calls a soft lock"
                )
            elif total > cap:
                print("  (rows lost mid-card, but no whole card dropped at this deck size)")
            else:
                print("  no truncation at this deck size")
        else:
            try:
                json.loads(piped)
            except json.JSONDecodeError as exc:
                print(f"  DEFECT: forwarded fragment is not valid JSON — {exc}")
                failures.append(
                    f"{skill}:{lineno}: head -{cap} truncated a {total}-line JSON "
                    f"document into a syntax error"
                )
            else:
                print("  parses as JSON (deck small enough to fit under the cap)")

    print("\n=== The engine offers no row bound for these renderers ===")
    help_text = goc(["--help"])
    for line in help_text.splitlines():
        if "--max-rows" in line and "Cap rows" in line:
            print(f"  {line.strip()}")
    print("  → --max-rows is board-only; --json and the -v table have no bound,")
    print("    so the skills reach for `head`, which cannot report what it removed.")
    print("    Contrast the board, which does report it: see the `… +N more` row")
    print("    added by the closed card")
    print("    board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden.")

    print("\n=== Verdict ===")
    if failures:
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("  PASS — no block truncated its output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
