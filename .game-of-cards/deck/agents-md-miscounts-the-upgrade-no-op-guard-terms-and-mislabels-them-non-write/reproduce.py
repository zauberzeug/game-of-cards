#!/usr/bin/env python3
"""Reproduce: AGENTS.md miscounts `upgrade()`'s no-op guard terms.

The "already at goc X — nothing to do is derived, never enumerated" paragraph
in AGENTS.md closed with:

    The two remaining terms next to the plan cover non-write work only — the
    interactive vendored-cleanup prompt and the legacy-briefing strip.

`upgrade()`'s short-circuit condition names three terms beside
`plan_has_effect`, and the third — `pending_skills_source` — is true exactly
when `_write_skills_source` would *write* `.game-of-cards/config.yaml`. So both
halves of the sentence were wrong: the count and the "non-write work only"
characterization. The code comment immediately above the guard already said
"plus the skills_source pin", so the contradiction was between two surfaces
describing the same eight-line block.

This script reads the guard out of the source rather than restating it, so it
keeps answering correctly if a future term is added or removed. Which terms
*write* is derived too: a `pending_*` term whose assignment calls something
with `probe=True` is asking a write-executor "would you change the file?",
which is the repo's established convention for exactly that question. A term
that gates a write without probing is not detected as a writer — the count
assertion is what catches that shape.

Before the fix: exit 1 with the mismatch printed.
After the fix:  exit 0 — AGENTS.md's count matches the parsed guard, it does
                not call the terms non-write while one of them writes, and it
                names the writing term so the reader knows which one.
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

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
}


def _upgrade_fn() -> ast.FunctionDef:
    tree = ast.parse((ROOT / "goc" / "install.py").read_text())
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
    )


def guard_terms(fn: ast.FunctionDef) -> list[str]:
    """The `pending_*` work signals ANDed into `upgrade()`'s short-circuit.

    Scoped to the `pending_*` prefix on purpose: that is the register AGENTS.md
    is counting ("Do not reintroduce a `pending_*` allowlist term ... the three
    remaining terms next to the plan"). The guard's other `not` operands
    (`agents_explicit`, `keep_local_skills`) are caller-flag overrides, not
    answers to "is there work?", so they are not what the sentence describes.
    """

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


def writing_terms(fn: ast.FunctionDef) -> dict[str, str]:
    """`pending_*` terms that gate a write, mapped to the executor they probe.

    A term assigned from a call carrying `probe=True` is asking that executor
    whether it would change a file — so the term is true exactly when the real
    call writes. Derived rather than listed so a new probing term joins the set
    without a hand-maintained register, the shape this paragraph forbids.
    """

    found: dict[str, str] = {}
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not target.id.startswith("pending_"):
            continue
        for call in ast.walk(node.value):
            if not isinstance(call, ast.Call):
                continue
            probes = any(
                kw.arg == "probe" and getattr(kw.value, "value", None) is True
                for kw in call.keywords
            )
            if probes:
                found[target.id] = ast.unparse(call.func)
    return found


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
    fn = _upgrade_fn()
    terms = guard_terms(fn)
    writers = {k: v for k, v in writing_terms(fn).items() if k in terms}
    count, sentence = claimed_count()

    print(f"upgrade() pending_* terms beside plan_has_effect: {len(terms)}")
    for term in terms:
        mark = f"  (WRITES to disk — probes {writers[term]})" if term in writers else ""
        print(f"  - {term}{mark}")
    print(f"\nAGENTS.md says: {sentence}")
    print(f"  claimed count: {count}")

    checks: list[tuple[bool, str]] = [
        (
            count == len(terms),
            f"AGENTS.md claims {count} remaining terms; upgrade() has {len(terms)} "
            f"({', '.join(terms)})",
        ),
        (
            not (writers and "non-write" in sentence),
            'AGENTS.md calls the remaining terms "non-write", but '
            + ", ".join(sorted(writers))
            + " gates a write to .game-of-cards/config.yaml",
        ),
        (
            # The prose names the pin by its config key, not by the local
            # variable, so match on the `pending_` prefix stripped off.
            all(term.removeprefix("pending_") in sentence for term in writers),
            "AGENTS.md's sentence does not name the writing term(s) "
            + ", ".join(sorted(writers))
            + " — a reader cannot tell which of the terms writes",
        ),
    ]
    failures = [why for ok, why in checks if not ok]

    print()
    if failures:
        print(f"DEFECT PRESENT ({len(failures)} of {len(checks)} assertions failed):")
        for failure in failures:
            print(f"  BUG: {failure}")
        return 1
    print("DEFECT ABSENT: AGENTS.md's sentence matches the guard it describes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
