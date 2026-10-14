#!/usr/bin/env python3
"""Does the shipped engine still name the deck script and schema file goc replaced?

Before goc was a package, a vendored `deck.py` script and a `SCHEMA.md` file sat
in the deck directory. The `goc` CLI and `goc/schema.yaml` replaced them, and
`shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced`
removed the names from the shipped skill templates. This script checks the
rest of the package:

1. builds the prompt `goc quality-pass --llm` hands the model, through the
   engine's own `_build_quality_prompt`, and prints any line naming either file;
2. sweeps every text file under `goc/` (the tree the wheel and all three plugin
   payloads ship) for either name.

Exits 1 while either check finds a line, 0 when neither does.
"""

from __future__ import annotations

import re
import sys
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
NAMES = re.compile(r"\b(deck\.py|SCHEMA\.md)\b")


def main() -> int:
    from goc import engine

    prompt = engine._build_quality_prompt([])
    in_prompt = [line.strip() for line in prompt.splitlines() if NAMES.search(line)]

    in_package = []
    for path in sorted((ROOT / "goc").rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if NAMES.search(line):
                in_package.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")

    print(f"quality-pass prompt lines naming a retired file: {len(in_prompt)}")
    for line in in_prompt:
        print(f"  - {line}")
    print(f"goc/ package lines naming a retired file: {len(in_package)}")
    for item in in_package:
        print(f"  - {item}")

    if in_prompt or in_package:
        return 1
    print("\nNeither the quality-pass prompt nor the goc/ package names deck.py or SCHEMA.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
