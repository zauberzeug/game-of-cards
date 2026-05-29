"""Reproduce: `goc decide` glues the new Decision block to the next ## heading.

Demonstrates that `replace_or_append_decision` loses the blank line that
separated the original `## Decision required` content from the next `## `
section, leaving `*Reasoning:* X` and `## NextSection` adjacent on
consecutive lines.

Run from anywhere:
    uv run python .game-of-cards/deck/goc-decide-omits-blank-line-before-following-section-heading/reproduce.py
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import replace_or_append_decision  # noqa: E402


def main() -> int:
    body = (
        "Pre-content.\n"
        "\n"
        "## Decision required\n"
        "\n"
        "What should we do?\n"
        "\n"
        "## Notes\n"
        "\n"
        "Some appendix material.\n"
    )

    result = replace_or_append_decision(body, "Pick A", "Simpler", "2026-05-29")

    print("=" * 60)
    print("INPUT (repr):")
    print(repr(body))
    print()
    print("OUTPUT (repr):")
    print(repr(result))
    print()
    print("OUTPUT (rendered):")
    print("-" * 60)
    print(result)
    print("-" * 60)

    # Find the line containing *Reasoning:* and the next line.
    lines = result.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("*Reasoning:*"):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            print(f"Line {i + 1}: {line!r}")
            print(f"Line {i + 2}: {next_line!r}")
            if next_line.startswith("## "):
                print()
                print("DEFECT CONFIRMED: heading runs straight into the Reasoning line "
                      "with no blank-line separator.")
                return 1
            print()
            print("OK: blank line separator present.")
            return 0
    print("Could not locate *Reasoning:* line — test setup error.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
