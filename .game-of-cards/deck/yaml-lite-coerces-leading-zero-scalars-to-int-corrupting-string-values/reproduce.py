"""Reproduce: yaml_lite coerces leading-zero decimal scalars to ints.

A bare frontmatter scalar like `008` or `0123` is a STRING under both
YAML 1.2 (canonical int is `0 | -?[1-9][0-9]*`) and PyYAML's 1.1
resolver (leading-zero non-octal runs are strings). yaml_lite's
`_INT_RE = ^-?\\d+$` over-matches them and `int()` strips the zeros,
silently changing the value.

Exits 0 when the parser preserves leading-zero scalars as strings
(post-fix) and 1 while the defect fires (pre-fix).
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

from goc._vendor import yaml_lite  # noqa: E402
from goc.engine import _worker_who  # noqa: E402

# (input, expected_value, expected_type)
CASES = [
    ("008", "008", str),
    ("009", "009", str),
    ("0123", "0123", str),
    ("00", "00", str),
    ("0", 0, int),
    ("42", 42, int),
    ("-5", -5, int),
]

bug = False
for raw, exp_val, exp_type in CASES:
    got = yaml_lite.safe_load(f"x: {raw}")["x"]
    ok = got == exp_val and type(got) is exp_type
    status = "ok" if ok else "[BUG]"
    print(
        f"{raw!r:6} -> {got!r:8} (type {type(got).__name__:3}) "
        f"EXPECTED {exp_val!r} ({exp_type.__name__}) {status}"
    )
    if not ok:
        bug = True

# Concrete consumer path: a hand-edited `worker: 008` is dropped by the
# worker filter and rejected by `goc validate`.
fm = yaml_lite.safe_load("worker: 008")
who = _worker_who(fm["worker"])
worker_ok = who == "008"
print(
    f"worker:008 -> _worker_who returns {who!r} "
    f"{'ok' if worker_ok else '(filter drops card; validate rejects as non-string)  [BUG]'}"
)
if not worker_ok:
    bug = True

sys.exit(1 if bug else 0)
