"""Demonstrate that `goc validate` accepts a card with `created` in the future.

Builds an isolated deck directory under a tempdir, writes a card whose
`created` field is ~73 years in the future, and runs `goc validate`.
The validator exits 0 — proving the temporal-ordering check is missing.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


CARD_FRONTMATTER = textwrap.dedent(
    """\
    ---
    title: sample-future-created
    status: open
    contribution: medium
    created: "2099-12-31T00:00:00Z"
    closed_at: null
    human_gate: none
    advances: []
    advanced_by: []
    tags: [bug]
    definition_of_done: |
      - [ ] TDD: placeholder
    ---

    # sample-future-created

    A card whose `created` timestamp is far in the future.
    """
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="goc-future-created-") as tmp:
        deck = Path(tmp) / ".game-of-cards" / "deck"
        card = deck / "sample-future-created"
        card.mkdir(parents=True)
        (card / "README.md").write_text(CARD_FRONTMATTER)
        (card / "log.md").write_text("")
        print(f"created sample card with created=2099-12-31T00:00:00Z")
        result = subprocess.run(
            ["uv", "run", "--project", str(repo_root), "goc", "validate"],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        print(f"goc validate exit code: {result.returncode}")
        if result.returncode == 0:
            print("DEFECT: validator accepts created ~73 years in the future")
            return 0
        print("FIX LANDED: validator rejected the future created timestamp:")
        print(result.stderr or result.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())
