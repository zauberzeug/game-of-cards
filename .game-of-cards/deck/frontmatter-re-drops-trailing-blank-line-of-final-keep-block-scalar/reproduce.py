"""Proof: parse_frontmatter drops the trailing blank line of a final |+ keep scalar.

A `|+` (keep) block scalar that ends in a blank line and is the LAST
frontmatter field does not round-trip through emit_frontmatter -> parse_frontmatter:
the closing `\n---` delimiter in FRONTMATTER_RE swallows the scalar's trailing
newline, so the value reads back one blank line short.

This is the parse-side mirror of the closed emitter-side card
`emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields`,
which fixed |+ *selection* in the emitter but explicitly scoped out this
FRONTMATTER_RE + safe_load parse boundary.

Exits 0 when the round-trip is faithful (fix landed), non-zero while the bug fires.
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


def main() -> int:
    failures = 0

    # Final field is a |+ keep scalar ending in a blank line.
    fm = {"title": "x", "summary": "ends with blank\n\n"}
    emitted = emit_frontmatter(fm)
    parsed, body = parse_frontmatter(emitted)
    got = parsed.get("summary")
    print("emitted frontmatter:")
    print(repr(emitted))
    want = "ends with blank\n\n"
    print(f"  expected summary: {want!r}")
    print(f"  actual   summary: {got!r}")
    if got != want:
        print("  -> FAIL: trailing blank line of final keep scalar was dropped")
        failures += 1
    else:
        print("  -> OK")

    # Control: same value with a sibling key after it must also round-trip.
    fm2 = {"title": "x", "summary": "ends with blank\n\n", "stage": None}
    parsed2, _ = parse_frontmatter(emit_frontmatter(fm2))
    if parsed2.get("summary") != "ends with blank\n\n":
        print("  -> FAIL: non-final keep scalar regressed")
        failures += 1

    # Body containing `---` must survive (no over-greedy capture).
    doc = "---\ntitle: y\n---\nbody with --- inside\nmore\n"
    data3, body3 = parse_frontmatter(doc)
    if body3 != "body with --- inside\nmore\n" or data3.get("title") != "y":
        print(f"  -> FAIL: body with --- mis-split: data={data3!r} body={body3!r}")
        failures += 1

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
