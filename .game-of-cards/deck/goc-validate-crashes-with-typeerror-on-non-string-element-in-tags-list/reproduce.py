"""Reproduce the `goc validate` crash on a non-string element in the `tags` field.

Run from a clean checkout:

    uv run python .game-of-cards/deck/goc-validate-crashes-with-typeerror-on-non-string-element-in-tags-list/reproduce.py

Expected output today (defect present): a `TypeError: unhashable type: 'list'`
traceback originating in `validate_card` at `engine.py:1207`, and a non-zero
exit code from the spawned `goc validate` invocation. After the fix, the
spawned validator should print a typed per-card error mentioning "tags: must
be a list of strings" and exit non-zero without a Python traceback.
"""

from __future__ import annotations

import os
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


def _write_offending_card(deck_dir: Path) -> Path:
    card = deck_dir / "card-with-non-string-tag-element"
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        "title: card-with-non-string-tag-element\n"
        'summary: ""\n'
        "status: open\n"
        "stage: null\n"
        "contribution: medium\n"
        "created: 2026-05-30\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug, [nested, list]]\n"
        "definition_of_done: |\n"
        "  - [ ] placeholder\n"
        "---\n"
        "\n"
        "# card-with-non-string-tag-element\n"
    )
    (card / "log.md").write_text("")
    return card


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-tags-typeerror-"))
    try:
        deck = tmp / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        (tmp / ".game-of-cards" / "config.yaml").write_text("{}\n")
        _write_offending_card(deck)

        result = subprocess.run(
            ["uv", "--project", str(REPO), "run", "goc", "validate"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
        )

        print("=== STDOUT ===")
        print(result.stdout, end="")
        print("=== STDERR ===")
        print(result.stderr, end="")
        print(f"=== EXIT CODE: {result.returncode} ===")

        combined = result.stdout + result.stderr
        has_typeerror = (
            "TypeError" in combined and "unhashable type" in combined
        )
        has_typed_error = (
            "must be a list of strings" in combined
            and "TypeError" not in combined
        )

        if has_typeerror:
            print(
                "\nFAIL: `goc validate` crashed with a raw `TypeError: unhashable "
                "type` traceback on the `tags` field (defect present)."
            )
            return 1
        if has_typed_error and result.returncode != 0:
            print(
                "\nPASS: `goc validate` reported a typed per-card error and exited "
                "non-zero without a Python traceback (defect fixed)."
            )
            return 0
        print(
            "\nUNEXPECTED: neither the TypeError traceback nor the typed per-card "
            "error appeared. Inspect the output above."
        )
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
