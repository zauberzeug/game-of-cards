"""Reproduce: `goc validate` accepts a card body that carries a copy of the frontmatter.

Runs `goc validate` from this source tree twice:

1. On a scratch deck in a temp dir (this repo's deck is untouched) holding
   three cards: one whose body repeats frontmatter key lines
   (`definition_of_done: |`, `title:`) outside a code fence, one whose body
   repeats a DoD checkbox line at the frontmatter's block indent, and one that
   shows the same lines inside a fenced code block.
2. On this repo's deck, to count the cards the check flags there.

Expected behavior (after the fix): the two spliced cards draw an advisory
`WARN BODY_REPEATS_FRONTMATTER`, the fenced card stays silent, `validate`
still exits 0, and this repo's deck draws no warning at all (its first run
found two cards; both were repaired).
Pre-fix behavior: no card draws the warning — the spliced bodies pass.

Exit codes: 0 = defect no longer fires, 1 = defect fires (a spliced body
passes silently) or the check misfires (the fenced card warns, or a card in
this repo's deck is flagged — repair a true positive, narrow the check for a
false one), 2 = the harness or a precondition is broken. The positive control
is that `validate` loads all three scratch cards (an `OK` line each) and
exits 0 on both decks; anything else exits 2 rather than passing for a verdict.

Run with:  uv run python .game-of-cards/deck/goc-validate-accepts-a-card-body-that-carries-a-second-copy-of-the-frontmatter/reproduce.py
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


REPO = _repo_root()
WARN = re.compile(r"^WARN BODY_REPEATS_FRONTMATTER (\S+): ", re.MULTILINE)

FRONTMATTER = (
    "---\n"
    "title: {title}\n"
    'summary: "Scratch card for the body-copy reproducer."\n'
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    'created: "2026-10-30T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: the real DoD item\n"
    "---\n"
)
SPLICED_KEYS = "title: spliced-key-lines\ndefinition_of_done: |\n"
SPLICED_DOD = "  - [ ] TDD: the real DoD item\n---\n"
CARDS = {
    "spliced-key-lines": f"\n# spliced-key-lines\n\n## Location\n\n{SPLICED_KEYS}\n",
    "spliced-dod-line": f"\n# spliced-dod-line\n\n## Decision required\n{SPLICED_DOD}\n",
    "fenced-example": (
        f"\n# fenced-example\n\n## Example\n\n```\n{SPLICED_KEYS}{SPLICED_DOD}```\n"
    ),
}
MUST_WARN = {"spliced-key-lines", "spliced-dod-line"}


def _validate(cwd: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("GOC_WORKTREE_DECK", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate", *flags],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        for title, body in CARDS.items():
            card_dir = cwd / ".game-of-cards" / "deck" / title
            card_dir.mkdir(parents=True)
            (card_dir / "README.md").write_text(FRONTMATTER.format(title=title) + body, encoding="utf-8")
            (card_dir / "log.md").write_text("", encoding="utf-8")
        scratch = _validate(cwd)
    print("$ goc validate   # scratch deck")
    print(f"  exit {scratch.returncode}")
    loaded = set(re.findall(r"^OK  (\S+)$", scratch.stdout, re.MULTILINE))
    if scratch.returncode != 0 or loaded != set(CARDS):
        print(f"HARNESS: scratch validate exit {scratch.returncode}, loaded {sorted(loaded)}:\n"
              f"{scratch.stderr}", file=sys.stderr)
        return 2
    warned = set(WARN.findall(scratch.stderr))
    for title in CARDS:
        print(f"  {title}: {'WARN' if title in warned else 'silent'}")

    deck = _validate(REPO, "--quiet")
    print("$ goc validate --quiet   # this repo's deck")
    print(f"  exit {deck.returncode}")
    if deck.returncode != 0:
        print(f"HARNESS: validate fails on this repo's deck:\n{deck.stderr}", file=sys.stderr)
        return 2
    flagged = WARN.findall(deck.stderr)
    print(f"  cards flagged: {len(flagged)}{' — ' + ', '.join(flagged) if flagged else ''}")

    if MUST_WARN - warned:
        print(f"SPLICED BODY PASSES SILENTLY: {sorted(MUST_WARN - warned)} — defect fires.")
        return 1
    if warned - MUST_WARN:
        print(f"MISFIRE: the check flags a fenced example: {sorted(warned - MUST_WARN)}.")
        return 1
    if flagged:
        print("DECK CARDS FLAGGED: repair each true positive, or narrow the check for a false one.")
        return 1
    print("Spliced bodies warn, the fenced example stays silent, the deck is clean — defect no longer fires.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
