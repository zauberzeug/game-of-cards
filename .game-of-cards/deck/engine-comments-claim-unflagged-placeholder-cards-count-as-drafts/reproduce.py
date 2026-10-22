#!/usr/bin/env python3
"""Comments claim `card_is_draft` catches unflagged placeholder scaffolds;
the engine does not.

An "unflagged placeholder scaffold" is a card that still carries both
`goc new` placeholders (the stub DoD and the stub body) but no
`draft: true` flag: a scaffold filed before the flag existed, or one whose
flag was stripped by hand. Several comments say the draft gate catches it.
`card_is_draft` reads the flag alone, and its own docstring says that is
deliberate.

This script does two things:

1. It searches the engine and the two artifacts that copied the claim for
   the claiming phrases.
2. It builds such a card with `goc new` plus a stripped flag, and asks the
   real CLI how it is treated: is it a draft, is it listed, is it pullable,
   and does `goc status ... superseded` refuse it the way it refuses a
   draft?

Exits 1 while the comments and the code disagree, in either direction.
Exits 0 once they agree: either the claims are gone and the card is
ordinary work, or a backstop was built and the claims became true.
"""

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

# Each phrase asserts that the draft gate also fires on the placeholders.
CLAIMS = (
    "flagless backstop in `card_is_draft`",
    "also catches flagless legacy scaffolds",
    "draft flag or surviving placeholder",
    "placeholder half of that predicate",
    "`card_is_draft` also fires on a surviving placeholder",
)
SCANNED = (
    "goc/engine.py",
    "tests/test_empty_query_result_line.py",
    ".game-of-cards/deck/zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/reproduce.py",
)

SUCCESSOR = """---
title: successor-card
summary: "An authored card to supersede into."
status: open
stage: null
contribution: medium
created: "2026-10-08T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [ ] TDD: a real criterion
---

# successor-card

A real body.
"""


def _flatten(text: str) -> str:
    """Collapse comment markers and line breaks so a phrase split across
    comment or docstring lines still matches."""
    lines = [re.sub(r"^\s*#\s?", "", line).strip() for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines))


def find_claims() -> list[tuple[str, str]]:
    found = []
    for rel in SCANNED:
        path = ROOT / rel
        if not path.exists():
            continue
        flat = _flatten(path.read_text())
        found.extend((rel, phrase) for phrase in CLAIMS if phrase in flat)
    return found


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("GOC_WORKER", None)
    env["NO_COLOR"] = "1"
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )


def observe_behavior() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        made = _goc(root, "new", "legacy-scaffold", "--gate", "none", "--tag", "story")
        assert made.returncode == 0, made.stderr
        readme = deck / "legacy-scaffold" / "README.md"
        text = readme.read_text()
        assert "draft: true\n" in text, text
        readme.write_text(text.replace("draft: true\n", ""))
        (deck / "successor-card").mkdir()
        (deck / "successor-card" / "README.md").write_text(SUCCESSOR)

        sys.path.insert(0, str(ROOT))
        from goc import engine

        card = engine.load_card(deck / "legacy-scaffold")
        listed = {c["title"] for c in json.loads(_goc(root, "--json").stdout)}
        ready = {c["title"] for c in json.loads(_goc(root, "--ready", "--json").stdout)}
        flagged = {
            c["title"]: c["draft"]
            for c in json.loads(_goc(root, "--status", "all", "--json").stdout)
        }
        publish = _goc(root, "publish", "legacy-scaffold", "--no-commit")
        supersede = _goc(
            root, "status", "legacy-scaffold", "superseded", "--by", "successor-card", "--no-commit"
        )
        return {
            "both placeholders present": engine.is_placeholder_scaffold(card),
            "card_is_draft": engine.card_is_draft(card),
            "--json draft field": flagged["legacy-scaffold"],
            "listed by `goc`": "legacy-scaffold" in listed,
            "listed by `goc --ready`": "legacy-scaffold" in ready,
            "`goc publish` output": (publish.stdout + publish.stderr).strip(),
            "`goc status superseded` refused": supersede.returncode != 0,
        }


def main() -> int:
    claims = find_claims()
    print("=== comments claiming the draft gate catches unflagged placeholder scaffolds ===")
    for rel, phrase in claims:
        print(f"  {rel}: {phrase!r}")
    if not claims:
        print("  (none)")

    behavior = observe_behavior()
    print("\n=== how goc treats an unflagged placeholder scaffold ===")
    for key, value in behavior.items():
        print(f"  {key}: {value}")

    gate_fires = bool(behavior["card_is_draft"])
    print("\n=== verdict ===")
    if bool(claims) != gate_fires:
        print(
            f"DEFECT: {len(claims)} claim(s) say the draft gate catches the card, "
            f"but card_is_draft returns {gate_fires}: it is listed, pullable and "
            "supersedable like authored work"
            if claims
            else "DEFECT: the draft gate catches the card but no comment says so"
        )
        return 1
    print("OK: the comments and card_is_draft agree on unflagged placeholder scaffolds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
