"""Reproduce the silent data loss in `_append_marker_block` when a briefing
file ends up with two `<!-- BEGIN GOC v... -->` markers and a single
`<!-- END GOC -->`. The non-greedy regex matches from the first BEGIN to
the only END, and `re.sub` replaces the whole region — discarding any
user-authored content between the two BEGIN markers."""

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

import re

from goc.install import GOC_BEGIN_RE, GOC_END, _append_marker_block


def main() -> int:
    corrupted = (
        "# Header\n"
        "\n"
        "User text above the block.\n"
        "\n"
        "<!-- BEGIN GOC v0.1.0 -->\n"
        "old-block-1 content\n"
        "<!-- BEGIN GOC v0.2.0 -->\n"
        "USER-AUTHORED CONTENT BETWEEN BEGINS (will be lost)\n"
        f"{GOC_END}\n"
        "\n"
        "User text below the block.\n"
    )

    print("=== input file (3 marker lines, 2 BEGINs + 1 END) ===")
    print(corrupted)

    pattern = re.compile(
        rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL
    )
    matches = pattern.findall(corrupted)
    print(f"=== number of regex matches: {len(matches)}")
    print("=== matched region (verbatim):")
    for m in matches:
        print(m)

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "AGENTS.md"
        target.write_text(corrupted)
        _append_marker_block(target, "fresh briefing body", header="# Header")
        result = target.read_text()

    print("=== file after _append_marker_block writes v0.3.0:")
    print(result)

    user_text_survived = "USER-AUTHORED CONTENT BETWEEN BEGINS" in result
    second_begin_survived = "<!-- BEGIN GOC v0.2.0 -->" in result
    print(f'=== "USER-AUTHORED CONTENT BETWEEN BEGINS" survived? {user_text_survived}')
    print(f"=== second BEGIN marker survived? {second_begin_survived}")

    if user_text_survived and second_begin_survived:
        print("=== PASS: intermediate content preserved")
        return 0
    print("=== FAIL: silent data loss")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
