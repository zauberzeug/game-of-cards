"""Reproduce: _split_flow mis-splits a flow collection on a backslash-escaped quote.

A `worker` mapping whose value contains a literal double-quote is emitted by
goc as `worker: {who: "a\""}`. On read-back, `_split_flow` (yaml_lite.py)
treats the escaped `\"` as a closing quote and swallows the structural comma,
losing the `where` key. Exits non-zero while the bug is live.
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

from goc import engine as e  # noqa: E402

failures = []

# Case 1: worker mapping with a double-quote in a value.
worker = {"who": 'a"', "where": "b"}
text = e.emit_frontmatter(
    {"title": "t", "status": "open", "worker": worker}, body="x"
)
emitted_line = next(l for l in text.splitlines() if l.startswith("worker:"))
parsed = e.parse_frontmatter(text)[0]["worker"]
print("--- case 1: worker mapping ---")
print("emitted :", repr(emitted_line))
print("parsed  :", repr(parsed))
print("expected:", repr(worker))
if parsed != worker:
    failures.append("worker mapping round-trip corrupted")

# Case 2: flow SEQUENCE element with an escaped double-quote.
# emit_frontmatter uses block lists, so author the flow sequence by hand to
# exercise the same _split_flow path the bug lives in.
fm_text = (
    "---\n"
    'title: t2\n'
    "status: open\n"
    # two elements: the first contains an escaped quote, then a comma separator
    'sample: ["a\\"", "b"]\n'
    "---\n"
    "body\n"
)
parsed2 = e.parse_frontmatter(fm_text)[0]["sample"]
expected2 = ['a"', "b"]
print("\n--- case 2: inline flow sequence with escaped quote ---")
print("source  : sample: [\"a\\\"\", \"b\"]")
print("parsed  :", repr(parsed2))
print("expected:", repr(expected2))
if parsed2 != expected2:
    failures.append("flow-sequence element with escaped quote mis-split")

print()
if failures:
    print("FAIL:", "; ".join(failures))
    sys.exit(1)
print("PASS: flow collections round-trip backslash-escaped quotes correctly")
sys.exit(0)
