#!/usr/bin/env python3
"""Prove two shipped templates cite a concrete goc card directory.

A consuming repo has none of goc's cards, so such a citation is dead on
arrival. Step 3 runs a real `goc install` into a throwaway git repo to show
the text actually reaches a consumer; step 4 shows why the guard that already
owns this rule does not catch it.
"""

from __future__ import annotations

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

# A `deck/` path naming a CONCRETE card directory. The `deck/<title>/`
# placeholder shorthand is explicitly not matched: `<` is excluded from the
# first character class, which is what keeps the 19 legitimate placeholder
# sites per skill tree out of the result.
CARD_PATH_RE = re.compile(r"(?<![\w./-])(?:\.game-of-cards/)?deck/([a-z0-9][a-z0-9-]*)/")

SHIPPED = (
    "goc/templates/game_of_cards/README.md",
    "goc/templates/game_of_cards/config.yaml",
    "goc/templates/skills/refine-deck/reference.md",
)

CITED = (
    "deck/goc-package-pyproject-and-pypi-release",
    ".game-of-cards/deck/goc-package-pyproject-and-pypi-release",
    ".game-of-cards/deck/package-pyproject-and-pypi-release",
    "deck/auto-validate-card-titles-summaries-and-dods",
    ".game-of-cards/deck/auto-validate-card-titles-summaries-and-dods",
)


def hits(text: str) -> list[tuple[int, str]]:
    return [
        (n, line.strip())
        for n, line in enumerate(text.splitlines(), 1)
        if CARD_PATH_RE.search(line)
    ]


def main() -> int:
    found = 0

    print("=== 1. concrete card directories cited by shipped templates ===")
    for rel in SHIPPED:
        for lineno, line in hits((ROOT / rel).read_text(encoding="utf-8")):
            found += 1
            print(f"  {rel}:{lineno}: {line}")

    print()
    print("=== 2. do the cited cards resolve in goc's own repo? ===")
    for cited in CITED:
        note = "   <- renamed to this" if (ROOT / cited).exists() else ""
        print(f"  {cited + '/':62}exists: {(ROOT / cited).exists()}{note}")

    print()
    print("=== 3. does the README text reach a fresh `goc install`? ===")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "install"],
            cwd=repo,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "HOME": tmp},
            check=True,
            capture_output=True,
        )
        installed = repo / ".game-of-cards" / "README.md"
        for lineno, line in hits(installed.read_text(encoding="utf-8")):
            print(f"  <fresh repo>/.game-of-cards/README.md:{lineno}: {line}")
        print(f"  <fresh repo>/deck/ created by install: {(repo / 'deck').exists()}")

    print()
    print("=== 4. does the standing guard cover both offenders? ===")
    # Why they shipped: the guard matched markdown-link syntax only, and swept
    # the skill trees only. Both lines are inline code, and one of them lives
    # in a tree that was never swept. Re-checked here so a future narrowing of
    # the guard reopens this card's defect visibly.
    from tests.test_skill_template_deck_links import (
        HISTORICAL_CARD_PATH_OFFENDERS,
        SWEPT_TREES,
        card_paths,
        deck_links,
    )

    for line in HISTORICAL_CARD_PATH_OFFENDERS:
        cited = line.strip().strip("`.() ")
        print(f"  link-only rule flags {cited[:52]:54}{bool(deck_links(line))}")
        print(f"  widened rule flags   {cited[:52]:54}{bool(card_paths(line))}")
    print(f"  guard sweeps goc/templates/skills:        "
          f"{'goc/templates/skills' in SWEPT_TREES}")
    print(f"  guard sweeps goc/templates/game_of_cards: "
          f"{'goc/templates/game_of_cards' in SWEPT_TREES}")

    print()
    if found:
        print(f"[FAIL] {found} shipped template line(s) cite a goc card directory no installed repo has")
        return 1
    print("[OK] no shipped template cites a concrete goc card directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
