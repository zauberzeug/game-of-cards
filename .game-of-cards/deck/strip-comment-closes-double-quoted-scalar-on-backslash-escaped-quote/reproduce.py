"""Reproduce: _strip_comment closes a double-quoted scalar on an escaped quote.

A double-quoted frontmatter value containing an emitter-produced `\\"`
followed later by ` #` is truncated on read, because _strip_comment
treats the escaped quote as the closing quote and then strips the
trailing ` #...` as a comment.

Exit 0 == round-trip is lossless (fixed). Exit 1 == corruption (bug present).
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

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402
from goc._vendor.yaml_lite import safe_load  # noqa: E402

ok = True

# 1. Direct safe_load of a double-quoted scalar with an escaped quote + ` #`.
got = safe_load('k: "a\\" b #c"\n')
expected = {"k": 'a" b #c'}
status = "OK " if got == expected else "BUG"
if got != expected:
    ok = False
print(f"[{status}] safe_load('k: \"a\\\" b #c\"')  ->  {got!r}   (expected {expected!r})")

# 2. Full emit -> parse round-trip via the frontmatter layer.
cases = ['a " b #c', 'measure 5" #wide', 'plain " quote no hash']
for s in cases:
    text = emit_frontmatter({"title": "t", "summary": s, "status": "open"}, body="x\n")
    fm, _ = parse_frontmatter(text)
    roundtrips = fm["summary"] == s
    if not roundtrips:
        ok = False
    status = "OK " if roundtrips else "BUG"
    print(f"[{status}] round-trip summary={s!r}  ->  {fm['summary']!r}")

# 3. Regression guards: behavior preserved by the prior sibling fixes.
#    - bare unbalanced quote still strips its trailing comment
#    - balanced double-quoted scalar keeps an interior ` #`
guards = [
    ("title: don't  # note\n", {"title": "don't"}),
    ('a: "x # y"\n', {"a": "x # y"}),
]
for src, want in guards:
    got = safe_load(src)
    good = got == want
    if not good:
        ok = False
    status = "OK " if good else "BUG"
    print(f"[{status}] guard safe_load({src.strip()!r})  ->  {got!r}   (expected {want!r})")

print()
if ok:
    print("PASS: escaped-quote values round-trip and comments are stripped correctly.")
    sys.exit(0)
else:
    print("FAIL: _strip_comment mis-handles a backslash-escaped quote in a double-quoted scalar.")
    sys.exit(1)
