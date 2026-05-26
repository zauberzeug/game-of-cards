"""Reproduce: `_append_marker_block` duplicates the GoC block when the
installed version carries a PEP 440 suffix.

`GOC_BEGIN_RE = r"<!-- BEGIN GOC v[\\d.]+ -->"` matches only digits and
dots, so a suffixed marker written to disk (e.g. `v0.0.20.post1.dev101`)
cannot be re-found by `_append_marker_block`, which then APPENDS a second
block instead of replacing in place.

Exits non-zero while the defect is present (two markers after two
appends, and/or a PEP 440 form the regex fails to match); exits zero once
the regex is broadened to match full version tokens.
"""

import re
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

import goc.install as install  # noqa: E402

ok = True

# --- Symptom 1: regex fails to match PEP 440 suffixed versions --------
forms = ["1.2.3", "1.2.3.post1", "0.0.20.post1.dev101", "1.0.0rc1", "2.0.0+local"]
print("=== regex vs PEP 440 forms ===")
for v in forms:
    marker = f"<!-- BEGIN GOC v{v} -->"
    matched = bool(install.GOC_BEGIN_RE.search(marker))
    print(f"  {v:25s} -> {matched}")
    if not matched:
        ok = False
if not ok:
    print("FAIL: GOC_BEGIN_RE cannot match a suffixed version marker")

# --- Symptom 2: append-twice duplicates the block on a suffixed ver ---
suffixed = "<!-- BEGIN GOC v0.0.20.post1.dev101 -->"
orig_begin = install.GOC_BEGIN
try:
    install.GOC_BEGIN = suffixed  # simulate a suffixed-version install
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "AGENTS.md"
        install._append_marker_block(target, "body one", header="# Title")
        install._append_marker_block(target, "body two", header="# Title")
        text = target.read_text()
        count = text.count("<!-- BEGIN GOC v")
        print("\n=== append-twice marker count ===")
        print("BEGIN-GOC markers after two appends:", count, "(expected 1)")
        if count != 1:
            print("FAIL: marker-bounded merge is not idempotent")
            ok = False
finally:
    install.GOC_BEGIN = orig_begin

print()
print("RESULT:", "PASS — marker merge is idempotent across PEP 440 versions"
      if ok else "FAIL — suffixed version breaks marker-block merge")
sys.exit(0 if ok else 1)
