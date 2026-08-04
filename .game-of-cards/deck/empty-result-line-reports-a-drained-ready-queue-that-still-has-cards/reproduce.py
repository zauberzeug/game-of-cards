#!/usr/bin/env python3
"""The empty-result line drops the `--status` filter that emptied the query.

`render_empty_query_line` treats `--ready` as *replacing* the status conjunct
rather than *adding* to it, but `filter_cards` applies both. So a query that
combines `--ready` with a contradictory `--status` empties for a reason the
message never names, and the sentence it does print — "ready: status open,
gate none, no active impediment" — is a false statement about the deck: the
ready predicate matched a card, as plain `goc --ready` proves on the very
same deck.

The probe builds a two-card scratch deck (one pullable, one closed) and
compares what `--ready` returns against what `--ready --status done` claims.

Exits 1 while the message omits the status filter, 0 once it names it.
"""

from __future__ import annotations

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


def run(deck_repo: Path, *argv: str) -> tuple[int, str]:
    """Run `goc <argv>` against the scratch repo; return (exit code, stdout+stderr)."""
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=str(deck_repo), env=env, capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


CARD = """---
title: {title}
summary: "Scratch card {title}."
status: {status}
stage: null
contribution: high
created: 2026-01-01
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [{box}] TDD: the scratch assertion holds
---

# {title}

Body authored so the card is not a draft scaffold.
"""


def build_deck(tmp: Path) -> Path:
    """A scratch repo with exactly one pullable card and one closed card.

    The pullable card is what makes the defect a *false* statement rather than
    merely an incomplete one: the ready predicate demonstrably matches it.

    Cards are written directly rather than via `goc new` + `goc publish`,
    because `publish` refuses an unauthored scaffold ("is still an unauthored
    scaffold (placeholder DoD and body)") — a card built by `new` alone stays
    `draft: true` and is hidden from every queue, which would make the probe
    silently non-discriminating.
    """
    deck = tmp / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    (tmp / ".game-of-cards" / "config.yaml").write_text("auto_commit: false\n")
    (tmp / "pyproject.toml").write_text('[project]\nname = "scratch"\n')
    subprocess.run(["git", "init", "-q", "."], cwd=str(tmp), check=False)

    for title, status, closed_at, box in (
        ("pullable-card", "open", "null", " "),
        ("closed-card", "done", "2026-02-02", "x"),
    ):
        (deck / title).mkdir()
        (deck / title / "README.md").write_text(
            CARD.format(title=title, status=status, closed_at=closed_at, box=box)
        )
        (deck / title / "log.md").write_text("")
    return tmp


READY_SENTENCE = "ready: status open, gate none, no active impediment"


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        deck_repo = build_deck(Path(td))

        _, ready_out = run(deck_repo, "--ready")
        # Count real table rows only. "No cards match (...)" must never be
        # mistaken for a data row, or the probe would report the defect on a
        # deck that has nothing to pull and prove nothing.
        ready_rows = [
            ln for ln in ready_out.splitlines()
            if ln.strip()
            and not ln.startswith(("TITLE", "---", "ACTIVE"))
            and "No cards match" not in ln
        ]

        print("the ready predicate on this deck\n")
        print(f"  `goc --ready`  -> {len(ready_rows)} row(s) matched")
        for ln in ready_rows:
            print(f"                    {ln.split()[0]}")
        if not any(ln.split()[0] == "pullable-card" for ln in ready_rows):
            print("\nFAIL: scratch deck has no pullable card; probe cannot")
            print("      discriminate a false claim from a true one.")
            print(f"      `goc --ready` said: {ready_out.strip()!r}")
            return 1

        print("\nwhat each zero-match variant says\n")
        variants = [
            ("`goc --ready --status done`", ("--ready", "--status", "done")),
            ("`goc --ready --done`", ("--ready", "--done")),
            ("`goc --ready --status active`", ("--ready", "--status", "active")),
        ]
        offences: list[str] = []
        for label, argv in variants:
            code, out = run(deck_repo, *argv)
            line = out.strip().splitlines()[-1] if out.strip() else "(nothing)"
            print(f"  exit {code}  {label}")
            print(f"           {line}")
            # The offence: the sentence asserts the ready predicate matched
            # nothing (while it matched `len(ready_rows)` cards above) and
            # never names the status filter that actually emptied the result.
            names_status = "status: done" in line or "status: active" in line
            if READY_SENTENCE in line and not names_status:
                offences.append(label)

        print()
        if offences:
            print(f"DEFECT: {len(offences)} of {len(variants)} variants claim the ready")
            print(f"        predicate matched nothing while it matches {len(ready_rows)} card(s),")
            print("        and none of them names the --status filter that emptied it.")
            for label in offences:
                print(f"          - {label}")
            return 1

        print(f"OK: all {len(variants)} variants name the status filter in effect.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
