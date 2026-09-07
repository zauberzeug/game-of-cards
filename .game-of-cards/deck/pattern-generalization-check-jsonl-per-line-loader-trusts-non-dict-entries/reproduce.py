#!/usr/bin/env python3
"""Falsification recipe for
`pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries`.

Feeds `_had_code_mutation` a JSONL transcript whose lines are valid JSON but
not objects. The card's hypothesis is that the per-line loader calls
`entry.get(...)` without a top-level `isinstance(entry, dict)` guard, so such
a line raises `AttributeError` and the Stop hook exits non-zero.

Exit 0 = defect reproduced (or, after a fix, the lines are skipped cleanly and
the script says so). The verdict is printed either way.
"""
import json
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

from goc.templates.hooks.pattern_generalization_check import _had_code_mutation

with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
    f.write("[1, 2, 3]\n")  # valid JSON, wrong shape
    f.write("null\n")  # valid JSON, wrong shape
    f.write('"oops"\n')  # valid JSON, wrong shape
    path = f.name

print("=== non-dict JSONL transcript lines ===")
try:
    result = _had_code_mutation(path)
    print(f"  _had_code_mutation returned {result} (no exception)")
    print("  VERDICT: non-dict lines are skipped — defect NOT reproduced")
except AttributeError as e:
    print(f"  CRASH: AttributeError: {e}")
    print("  VERDICT: defect reproduced — a non-dict transcript line kills the Stop hook")

# Control: a well-formed dict line must still be read, so a green run is a
# claim about shape-guarding rather than about the loader having stopped.
with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
    f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": "goc/engine.py"}}]}}) + "\n")
    ctrl = f.name

print("=== control: a well-formed tool_use line ===")
print(f"  _had_code_mutation returned {_had_code_mutation(ctrl)} (expected True)")
