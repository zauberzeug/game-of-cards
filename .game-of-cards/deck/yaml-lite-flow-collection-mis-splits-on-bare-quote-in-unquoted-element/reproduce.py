"""Reproduce: `_split_flow` flips quote-mode on a bare quote in an unquoted
flow element, swallowing the comma separator and dropping every later field.

A hand-authored card whose `worker` mapping carries an apostrophe in a bare
(unquoted) value — `worker: {who: o'connor, where: feature/x}` — parses to a
single corrupted key: `{'who': "o'connor, where: feature/x"}`. The `where`
field is silently lost.

Run on a clean checkout:
    uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exits 0 when the defect is FIXED, 1 while it still fires.
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

from goc._vendor.yaml_lite import _split_flow  # noqa: E402
from goc.engine import parse_frontmatter  # noqa: E402

ok = True

# 1) Direct: a flow mapping element with a bare apostrophe.
inner = "who: o'connor, where: feature/x"
parts = _split_flow(inner)
print(f"_split_flow({inner!r})")
print(f"  -> {parts}")
if len(parts) != 2:
    print(f"  FAIL: expected 2 elements, got {len(parts)} (comma swallowed by bare quote)")
    ok = False
else:
    print("  ok: split into 2 elements")

# 2) Direct: a flow sequence with a bare apostrophe.
seq = "a'b, c"
parts2 = _split_flow(seq)
print(f"_split_flow({seq!r})")
print(f"  -> {parts2}")
if len(parts2) != 2:
    print(f"  FAIL: expected 2 elements, got {len(parts2)}")
    ok = False
else:
    print("  ok: split into 2 elements")

# 3) End-to-end through the real frontmatter loader: a hand-authored worker
#    mapping silently loses the `where` field.
text = """---
title: foo
worker: {who: o'connor, where: feature/x}
tags: [bug, api-contract]
---
body
"""
fm, _ = parse_frontmatter(text)
worker = fm.get("worker")
print(f"parse_frontmatter worker -> {worker!r}")
if not isinstance(worker, dict) or worker.get("where") != "feature/x" or worker.get("who") != "o'connor":
    print("  FAIL: worker mapping corrupted (where dropped / who mangled)")
    ok = False
else:
    print("  ok: who and where parsed correctly")

# 4) Regression guard: a genuinely quoted element with an internal comma must
#    still NOT split (the comma is content inside the quotes).
quoted = '"x, y", z'
parts3 = _split_flow(quoted)
print(f"_split_flow({quoted!r})")
print(f"  -> {parts3}")
if len(parts3) != 2 or parts3[0].strip() != '"x, y"':
    print(f"  FAIL: quoted element regressed: {parts3}")
    ok = False
else:
    print("  ok: quoted internal comma preserved")

print()
print("RESULT:", "PASS (defect fixed)" if ok else "FAIL (defect fires)")
sys.exit(0 if ok else 1)
