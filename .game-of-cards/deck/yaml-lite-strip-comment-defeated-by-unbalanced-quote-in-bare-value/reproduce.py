"""Reproduce: yaml-lite's _strip_comment enters quote mode on a lone quote
char in a *bare* (unquoted) value (e.g. the apostrophe in `don't`) and never
exits, so a trailing `# comment` is never recognized and is folded into the
value. Real YAML strips that comment.

Exit 0 == comments stripped from bare values AND preserved inside genuinely
quoted runs (defect fixed). Exit 1 == at least one case is wrong (defect fires).
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

from goc._vendor.yaml_lite import safe_load  # noqa: E402

# (input document, key, expected value)
cases = [
    # The bug: lone apostrophe in a bare value must not suppress comment strip.
    ("title: don't  # note", "title", "don't"),
    ("a: 5 o'clock # x", "a", "5 o'clock"),
    # Control: bare value with no quote — comment already stripped correctly.
    ("b: plain value  # cmt", "b", "plain value"),
    # Regression guard: a `#` inside a genuinely *quoted* run is NOT a comment.
    ('a: "x # y"', "a", "x # y"),
    # Regression guard: a trailing comment after a balanced quoted scalar IS
    # stripped (the quote run closes, then the comment is recognized).
    ('c: "quoted" # tail', "c", "quoted"),
]

failures = 0
for doc, key, expected in cases:
    got = safe_load(doc).get(key)
    ok = got == expected
    flag = "OK  " if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{flag}: {doc!r:28} -> {key}={got!r} (expected {expected!r})")

print()
if failures:
    print(f"DEFECT: {failures}/{len(cases)} cases wrong")
    sys.exit(1)
print("OK: comments stripped from bare values, preserved inside quoted runs")
sys.exit(0)
