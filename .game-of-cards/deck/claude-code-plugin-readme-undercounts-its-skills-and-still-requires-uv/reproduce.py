#!/usr/bin/env python3
"""Prove `claude-plugin/README.md` misdescribes the payload it ships.

Two independent claim clusters are checked against the tree that IS the
payload:

1. Skill catalogue — the `**N skills**` count, the `| \\`skill\\` |` table rows,
   and the "all N skills are immediately available" restatement, versus the
   directories actually shipped under `claude-plugin/skills/`.
2. Host prerequisite — the intro's "runs via the `uv` tool manager" claim,
   versus `claude-plugin/bin/goc` (which execs `python3 -m goc.cli`) and the
   same README's own Install/Requirements sections.

Exit 0 once every claim agrees with the tree; non-zero while any drifts.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
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
README = ROOT / "claude-plugin" / "README.md"
SKILLS_DIR = ROOT / "claude-plugin" / "skills"
WRAPPER = ROOT / "claude-plugin" / "bin" / "goc"

# `| `skill-name` | Purpose |` — first cell of a catalogue table row.
_TABLE_ROW = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|", re.MULTILINE)
_BOLD_COUNT = re.compile(r"\*\*(\d+) skills\*\*")
_PROSE_COUNT = re.compile(r"all (\d+)\s+\n?skills are immediately available")


def shipped_skills() -> set[str]:
    """Skill directories actually present in the Claude plugin payload."""
    return {p.name for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file()}


def main() -> int:
    text = README.read_text()
    shipped = shipped_skills()
    catalogued = set(_TABLE_ROW.findall(text))

    failures: list[str] = []

    print("=== 1. skill catalogue ===")
    print(f"shipped under claude-plugin/skills/ : {len(shipped)}")
    print(f"rows in README catalogue table      : {len(catalogued)}")
    missing = sorted(shipped - catalogued)
    extra = sorted(catalogued - shipped)
    print(f"shipped but not catalogued          : {missing}")
    print(f"catalogued but not shipped          : {extra}")
    if missing or extra:
        failures.append(
            f"catalogue table disagrees with claude-plugin/skills/ "
            f"(missing={missing}, extra={extra})"
        )

    bold = _BOLD_COUNT.search(text)
    if bold is None:
        failures.append("no `**N skills**` count claim found in README")
        print("bold count claim                    : <absent>")
    else:
        claimed = int(bold.group(1))
        print(f"bold count claim                    : {claimed}")
        if claimed != len(shipped):
            failures.append(
                f"README claims **{claimed} skills**, payload ships {len(shipped)}"
            )

    prose = _PROSE_COUNT.search(text)
    if prose is None:
        print("prose count restatement             : <absent>")
    else:
        restated = int(prose.group(1))
        print(f"prose count restatement             : {restated}")
        if restated != len(shipped):
            failures.append(
                f"README's 'all {restated} skills are immediately available' "
                f"restates a count the payload contradicts ({len(shipped)})"
            )

    print()
    print("=== 2. host prerequisite ===")
    wrapper_text = WRAPPER.read_text()
    wrapper_uses_uv = re.search(r"\buv\s+run\b|\buv\b\s*(?:tool|venv)", wrapper_text) is not None
    print(f"bin/goc actually shells out via uv  : {wrapper_uses_uv}")
    uv_claim_lines = [
        (i, line.strip())
        for i, line in enumerate(text.splitlines(), start=1)
        if "uv` tool manager" in line
    ]
    for lineno, line in uv_claim_lines:
        print(f"README:{lineno}: {line}")
    if uv_claim_lines and not wrapper_uses_uv:
        failures.append(
            "README intro advertises the `uv` tool manager as the CLI's runtime, "
            "but claude-plugin/bin/goc execs `python3 -m goc.cli` (no uv)"
        )
    if not uv_claim_lines:
        print("README:  no `uv` tool manager claim  : OK")

    print()
    if failures:
        print(f"[FAIL] {len(failures)} claim(s) drifted from the shipped payload:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[OK] every README claim agrees with the shipped payload.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
