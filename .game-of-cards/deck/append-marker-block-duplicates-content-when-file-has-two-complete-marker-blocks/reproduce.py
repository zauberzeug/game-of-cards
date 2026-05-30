"""Reproduce: `_append_marker_block` duplicates GoC blocks when a file has two complete BEGIN+END pairs.

Run with: `uv run python deck/append-marker-block-duplicates-content-when-file-has-two-complete-marker-blocks/reproduce.py`

Exits non-zero (DEFECT FIRES) until the bug is fixed; exits zero once
the fixed implementation either consolidates to one block, or refuses
the malformed input with a clear error (per the sibling card's
decision).
"""

from __future__ import annotations

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


sys.path.insert(0, str(_repo_root()))


from goc.install import GOC_BEGIN_RE, _append_marker_block  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "AGENTS.md"
        original = (
            "# Header\n\n"
            "User text above.\n\n"
            "<!-- BEGIN GOC v0.1.0 -->\n"
            "old block one\n"
            "<!-- END GOC -->\n\n"
            "User text between two complete blocks.\n\n"
            "<!-- BEGIN GOC v0.2.0 -->\n"
            "old block two\n"
            "<!-- END GOC -->\n\n"
            "User text below.\n"
        )
        target.write_text(original)

        print("=== BEFORE _append_marker_block ===")
        print(target.read_text())

        try:
            _append_marker_block(target, "NEW briefing content", header="# Agent Guidelines")
        except Exception as exc:  # noqa: BLE001
            # If a future fix decides to fail loudly on malformed input,
            # surface the error here. Treat that as the fixed shape.
            print("=== _append_marker_block REFUSED the input (fixed behaviour) ===")
            print(f"{type(exc).__name__}: {exc}")
            return 0

        after = target.read_text()
        print("=== AFTER _append_marker_block ===")
        print(after)

        begin_count = len(GOC_BEGIN_RE.findall(after))
        print(f"BEGIN-marker count after rewrite: {begin_count}")
        if begin_count > 1:
            print("DEFECT FIRES — file ends with >1 GoC marker block; duplication is silent.")
            return 1
        print("OK — file ends with at most one GoC marker block.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
