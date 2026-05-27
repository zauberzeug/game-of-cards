"""Demonstrate that mutate_frontmatter_field corrupts values containing
backslashes, because new_value is interpolated into the *replacement*
argument of re.sub (which interprets backslash escapes).

Run: uv run python deck/<title>/reproduce.py
Exits non-zero while the defect is live, zero once it is fixed.
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

from goc.engine import mutate_frontmatter_field, _yaml_inline, parse_frontmatter  # noqa: E402

failures = 0

# Case 1: a Windows-style path with backslashes (e.g. an LLM summary rewrite
# via `goc quality-pass --llm`, whose caller _apply_summary_rewrite passes
# _yaml_inline(summary) straight into mutate_frontmatter_field).
original = r"path C:\Users\foo and a \n literal"
card = "---\nsummary: old\nstatus: open\n---\nbody\n"
written = mutate_frontmatter_field(card, "summary", _yaml_inline(original))
roundtrip = parse_frontmatter(written)[0]["summary"]
print("case 1 (summary with backslashes):")
print("  original   :", repr(original))
print("  round-trip :", repr(roundtrip))
print("  OK?        :", roundtrip == original)
if roundtrip != original:
    failures += 1

# Case 2: a backreference-shaped value. re.sub reads \g<...> / \1 in the
# replacement; _yaml_inline doubles the backslash so it does not crash, but
# the doubling is then collapsed by re.sub and the value is mangled.
original2 = r"backref \g<1> and group \1"
written2 = mutate_frontmatter_field(card, "summary", _yaml_inline(original2))
roundtrip2 = parse_frontmatter(written2)[0]["summary"]
print("case 2 (summary with regex-backreference text):")
print("  original   :", repr(original2))
print("  round-trip :", repr(roundtrip2))
print("  OK?        :", roundtrip2 == original2)
if roundtrip2 != original2:
    failures += 1

print()
if failures:
    print(f"FAIL: {failures} value(s) did not round-trip through mutate_frontmatter_field")
    sys.exit(1)
print("PASS: all values round-trip cleanly")
