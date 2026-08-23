#!/usr/bin/env python3
"""Demonstrate the STRUCTURED_PREFIXES blind spot in the card-frontmatter guard.

The repo-local guard `scripts/check_card_frontmatter_yaml.py` exists to catch
card frontmatter that `goc validate` accepts but a strict YAML parser refuses.
It early-`continue`s on any value opening with `"`, `'`, `[` or `{`, so a value
whose *quoting itself* is malformed is never examined.

Part 1 enumerates the skipped value forms and reports, for each, what strict
YAML does, what the vendored parser does, and whether the guard fires. A row
where strict YAML REFUSES, the vendored parser ACCEPTS, and the guard is SILENT
is a divergence the guard was built to catch and does not.

Part 2 runs the reachability path on a real card in this deck: drop the
backslashes the emitter added to a summary's interior quotes — the single most
plausible hand-edit — then re-check. The guard prints "strict-YAML clean".

Part 3 counts how many live card summaries carry an emitter-escaped interior
quote, i.e. how many cards are one dropped backslash from the hazard.

Exit code: 0 when the blind spot is closed (no divergent row is SILENT), 1
while it is open. So this script exits 1 today and 0 once the card is fixed.

PyYAML is imported as the strict reference. It is a dev-only import for this
script, not a goc runtime dependency; the script skips (exit 0) if it is
absent, so it never fails the build for the wrong reason.
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

try:
    import yaml  # strict reference parser
except ImportError:  # pragma: no cover - environment without PyYAML
    print("SKIP: PyYAML not importable; cannot act as the strict reference.")
    sys.exit(0)

from goc._vendor import yaml_lite  # noqa: E402
from goc.engine import FRONTMATTER_RE  # noqa: E402
from scripts.check_card_frontmatter_yaml import flag_frontmatter  # noqa: E402

# One case per value form the guard's STRUCTURED_PREFIXES tuple skips.
CASES = (
    ("double-quoted, interior quote", 'summary: "the verb: refuses "unchecked" boxes"'),
    ("double-quoted, unterminated", 'summary: "opens but never closes'),
    ("single-quoted, interior quote", "summary: 'it's a value: here'"),
    ("flow mapping, nested colon", "worker: {who: a: b}"),
    ("flow list, unterminated", "tags: [bug, api-contract"),
    ("flow mapping, unterminated", "worker: {who: claude"),
)


def _strict(block: str) -> str:
    try:
        yaml.safe_load(block)
    except Exception as exc:
        return f"REFUSES ({type(exc).__name__})"
    return "ACCEPTS"


def _lite(block: str) -> str:
    try:
        yaml_lite.safe_load(block)
    except Exception as exc:
        return f"REFUSES ({type(exc).__name__})"
    return "ACCEPTS"


print("=" * 78)
print("Part 1 — the value forms the guard skips, by parser verdict")
print("=" * 78)
print(f"{'value form':32} {'strict YAML':24} {'yaml_lite':10} guard")
print("-" * 78)

divergent_and_silent = []
for name, line in CASES:
    block = f"title: t\n{line}\nstatus: open\n"
    strict, lite = _strict(block), _lite(block)
    guard = "FLAGS" if flag_frontmatter(block) else "SILENT"
    print(f"{name:32} {strict:24} {lite:10} {guard}")
    if strict.startswith("REFUSES") and lite == "ACCEPTS" and guard == "SILENT":
        divergent_and_silent.append(name)

print()
print(f"{len(divergent_and_silent)} form(s) refused by strict YAML, accepted by the")
print("vendored parser, and invisible to the guard:")
for name in divergent_and_silent:
    print(f"  - {name}")

print()
print("=" * 78)
print("Part 2 — reachability on a real card in this deck")
print("=" * 78)

deck = ROOT / ".game-of-cards" / "deck"
victim = next(
    (
        readme
        for readme in sorted(deck.glob("*/README.md"))
        if re.search(r'^summary: ".*\\"', readme.read_text(encoding="utf-8"), re.MULTILINE)
    ),
    None,
)

if victim is None:
    print("No card summary carries an escaped interior quote; skipping Part 2.")
else:
    original = victim.read_text(encoding="utf-8")
    # The hand-edit: retype the summary, losing the emitter's \" escapes.
    edited = re.sub(
        r"^summary: .*$",
        lambda m: m.group(0).replace('\\"', '"'),
        original,
        count=1,
        flags=re.MULTILINE,
    )
    block = FRONTMATTER_RE.match(edited).group(1)
    summary_line = next(ln for ln in block.splitlines() if ln.startswith("summary:"))

    print(f"card         : {victim.parent.name}")
    print(f"edit         : dropped the \\ before each interior \" in `summary`")
    print(f"summary now  : {summary_line[:96]}...")
    print(f"strict YAML  : {_strict(block)}")
    print(f"yaml_lite    : {_lite(block)}")
    print(f"repo guard   : {'FLAGS' if flag_frontmatter(block) else 'SILENT (reports clean)'}")

print()
print("=" * 78)
print("Part 3 — how many cards are one dropped backslash away")
print("=" * 78)

readmes = sorted(deck.glob("*/README.md"))
exposed = [
    r.parent.name
    for r in readmes
    if re.search(r'^summary: ".*\\"', r.read_text(encoding="utf-8"), re.MULTILINE)
]
print(f"cards in deck                            : {len(readmes)}")
print(f"summaries with an escaped interior quote : {len(exposed)}")

print()
if divergent_and_silent:
    print(
        f"FAIL: {len(divergent_and_silent)} strict-YAML-refusing value form(s) pass "
        "both `goc validate` and the guard."
    )
    sys.exit(1)
print("PASS: every strict-YAML-refusing form the guard skips is now flagged.")
sys.exit(0)
