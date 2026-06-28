"""Folded-scalar chomp/indent variants silently misparse instead of raising.

The vendored yaml-lite parser is documented to raise ParseError on the
unsupported folded-scalar (`>`) feature. The guard at
goc/_vendor/yaml_lite.py is an exact-string `rest == ">"` check, so only
the bare `>` raises; every variant carrying a chomping (`-`/`+`) or
explicit-indent (`2`, ...) indicator slips past, is returned as the literal
header string, and drops every frontmatter field that follows.

Exits 0 when every folded variant raises (defect fixed); exits 1 when any
variant silently misparses (defect present).
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

from goc._vendor import yaml_lite as y  # noqa: E402

VARIANTS = [">", ">-", ">+", ">2", ">2-", ">2+"]

misparsed = []
for ind in VARIANTS:
    doc = f"title: t\nsummary: {ind}\n  folded line one\n  folded line two\nstatus: open\ntags: [a]"
    try:
        result = y.safe_load(doc)
    except y.ParseError as e:
        print(f"{ind!r:6} -> ParseError (correct): {e}")
        continue
    dropped = [k for k in ("status", "tags") if k not in result]
    note = f"   [MISPARSE: {', '.join(dropped)} dropped]" if dropped else "   [MISPARSE]"
    print(f"{ind!r:6} -> {result}{note}")
    misparsed.append(ind)

if misparsed:
    print(f"\nDEFECT CONFIRMED: {len(misparsed)} folded variant(s) misparsed instead of raising")
    sys.exit(1)

print("\nOK: every folded-scalar variant raises ParseError")
sys.exit(0)
