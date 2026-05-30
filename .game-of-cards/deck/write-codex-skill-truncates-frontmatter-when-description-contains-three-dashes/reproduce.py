#!/usr/bin/env python3
"""Reproduce: `_write_codex_skill` truncates frontmatter and corrupts body
when a skill's `description` value contains the literal substring `---`.

Run from the repo root:

    uv run python .game-of-cards/deck/write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes/reproduce.py

Exits 1 if the bug is present (current behavior), 0 once it is fixed.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Make `goc.install` importable without `uv pip install -e .`
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from goc.install import _write_codex_skill  # noqa: E402


SRC_FRONTMATTER = (
    "---\n"
    "name: example-skill\n"
    'description: "Use --- as a section delimiter in your prose"\n'
    "---\n"
    "\n"
    "# Body\n"
    "\n"
    "Body content here.\n"
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src.md"
        dst = Path(td) / "dst.md"
        src.write_text(SRC_FRONTMATTER)
        _write_codex_skill(src, dst, skill_name="example-skill")
        ported = dst.read_text()

    # The frontmatter is expected to faithfully preserve the description.
    # Find the codex description line.
    desc_line = next(
        (ln for ln in ported.splitlines() if ln.startswith("description:")),
        "",
    )
    # Parse: `description: <json-string>` — the value is JSON-encoded by the porter.
    try:
        value = json.loads(desc_line.removeprefix("description: ").strip())
    except (json.JSONDecodeError, ValueError):
        value = None

    expected = "Use --- as a section delimiter in your prose"
    if value == expected:
        print("OK — description preserved end-to-end:")
        print(f"  got: {value!r}")
        return 0

    print("FAIL — `_write_codex_skill` corrupted the skill:")
    print(f"  expected description: {expected!r}")
    print(f"  observed description: {value!r}")
    print("  full ported output:")
    print("    " + ported.replace("\n", "\n    "))
    return 1


if __name__ == "__main__":
    sys.exit(main())
