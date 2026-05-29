"""Reproduce: `goc unadvance foo --by foo` corrupts a card with self-edges.

Exits 0 while the defect fires. Once the chosen fix lands (Option A:
caller rejects with exit 2; Option B: helper clears both lists cleanly),
the assertion at the bottom flips and this script will exit 1 — at which
point the DoD TDD checkbox is satisfied (the defect "no longer fires").
"""
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


REPO = _repo_root()

CARD = """---
title: foo
summary: "A test card."
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances:
  - foo
advanced_by:
  - foo
tags: [story]
definition_of_done: |
  - [ ] something
---

# foo

body
"""


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-self-unadvance-"))
    try:
        deck = tmp / ".game-of-cards" / "deck" / "foo"
        deck.mkdir(parents=True)
        readme = deck / "README.md"
        readme.write_text(CARD)

        print("--- BEFORE: foo card frontmatter ---")
        for line in CARD.splitlines()[8:13]:
            print(line)

        print("--- run: goc unadvance foo --by foo ---")
        result = subprocess.run(
            ["uv", "run", "--project", str(REPO),
             "goc", "unadvance", "foo", "--by", "foo", "--no-commit"],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        print(f"exit={result.returncode}")

        print("--- AFTER ---")
        after = readme.read_text()
        # Print the same frontmatter slice the BEFORE block showed.
        slice_lines = after.splitlines()
        # Find the advances/advanced_by region.
        for i, line in enumerate(slice_lines):
            if line.startswith("advances"):
                for line in slice_lines[i:i + 5]:
                    print(line)
                break

        # Detect the half-edge: one list lost `foo`, the other kept it.
        has_advances_foo = "\nadvances:\n  - foo" in after or "advances: [foo]" in after
        has_advanced_by_foo = "\nadvanced_by:\n  - foo" in after or "advanced_by: [foo]" in after
        half_edge = has_advances_foo != has_advanced_by_foo

        print()
        if half_edge:
            print("DEFECT FIRES: card is in a half-edge state "
                  f"(advances has foo={has_advances_foo}, advanced_by has foo={has_advanced_by_foo}).")
            return 0
        if result.returncode != 0:
            print("DEFECT NO LONGER FIRES: unadvance rejected the self-target call.")
            return 1
        if not has_advances_foo and not has_advanced_by_foo:
            print("DEFECT NO LONGER FIRES: unadvance cleared both halves cleanly.")
            return 1
        print("UNEXPECTED STATE — both lists still carry foo; reproducer needs review.")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
