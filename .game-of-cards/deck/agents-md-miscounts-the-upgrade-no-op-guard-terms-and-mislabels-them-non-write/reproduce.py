#!/usr/bin/env python3
"""Reproduce: AGENTS.md miscounts `upgrade()`'s no-op guard terms.

The "already at goc X — nothing to do is derived, never enumerated" paragraph
in AGENTS.md closes with:

    The two remaining terms next to the plan cover non-write work only — the
    interactive vendored-cleanup prompt and the legacy-briefing strip.

`upgrade()`'s short-circuit condition names three terms beside
`plan_has_effect`, and the third — `pending_skills_source` — is true exactly
when `_write_skills_source` would *write* `.game-of-cards/config.yaml`. So both
halves of the sentence are wrong: the count and the "non-write work only"
characterization. The code comment immediately above the guard already says
"plus the skills_source pin", so the contradiction is between two surfaces
describing the same eight-line block.

This script reads the guard out of the source rather than restating it, so it
keeps answering correctly if a future term is added or removed.

Before the fix: exit 1 with the mismatch printed.
After the fix:  exit 0 — AGENTS.md's count matches the parsed guard and no
                term it calls non-write actually writes.
"""

from __future__ import annotations

import ast
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

# Terms that write to disk when true, so a sentence calling the guard's
# remaining terms "non-write work only" is false if any of these appear.
WRITING_TERMS = {"pending_skills_source"}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
}


def guard_terms() -> list[str]:
    """The `pending_*` work signals ANDed into `upgrade()`'s short-circuit.

    Scoped to the `pending_*` prefix on purpose: that is the register AGENTS.md
    is counting ("Do not reintroduce a `pending_*` allowlist term ... the two
    remaining terms next to the plan"). The guard's other `not` operands
    (`agents_explicit`, `keep_local_skills`) are caller-flag overrides, not
    answers to "is there work?", so they are not what the sentence describes.
    """

    tree = ast.parse((ROOT / "goc" / "install.py").read_text())
    fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
    )
    for node in ast.walk(fn):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.BoolOp):
            continue
        names = [
            operand.operand.id
            for operand in node.test.values
            if isinstance(operand, ast.UnaryOp)
            and isinstance(operand.op, ast.Not)
            and isinstance(operand.operand, ast.Name)
        ]
        if "plan_has_effect" in names:
            return [name for name in names if name.startswith("pending_")]
    raise RuntimeError("short-circuit guard not found in upgrade()")


def claimed_count() -> tuple[int, str]:
    """The count AGENTS.md claims, plus the sentence it claims it in."""

    text = (ROOT / "AGENTS.md").read_text()
    match = re.search(
        r"The (\w+) remaining terms? next to the plan[^.]*\.", text, re.DOTALL
    )
    if match is None:
        raise RuntimeError("the 'remaining terms' sentence is gone from AGENTS.md")
    word = match.group(1).lower()
    if word not in NUMBER_WORDS:
        raise RuntimeError(f"unparseable count word: {word!r}")
    return NUMBER_WORDS[word], " ".join(match.group(0).split())


def main() -> int:
    terms = guard_terms()
    count, sentence = claimed_count()
    writers = [term for term in terms if term in WRITING_TERMS]

    print(f"upgrade() pending_* terms beside plan_has_effect: {len(terms)}")
    for term in terms:
        mark = "  (WRITES to disk)" if term in WRITING_TERMS else ""
        print(f"  - {term}{mark}")
    print(f"\nAGENTS.md says: {sentence}")
    print(f"  claimed count: {count}")

    failures: list[str] = []
    if count != len(terms):
        failures.append(
            f"AGENTS.md claims {count} remaining terms; upgrade() has {len(terms)} "
            f"({', '.join(terms)})"
        )
    if writers:
        failures.append(
            "AGENTS.md calls the remaining terms \"non-write work only\", but "
            + ", ".join(writers)
            + " gates a write to .game-of-cards/config.yaml"
        )

    print()
    if failures:
        print(f"DEFECT PRESENT ({len(failures)} of 2 assertions failed):")
        for failure in failures:
            print(f"  BUG: {failure}")
        return 1
    print("DEFECT ABSENT: AGENTS.md's sentence matches the guard it describes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
