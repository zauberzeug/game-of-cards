"""Reproduce: the frontmatter emitter mangles block-scalar values whose
content lines carry their own leading whitespace.

Two symptoms, same root cause in `_emit_block_field`:
  A. first content line more-indented than the rest -> re-parse RAISES.
  B. every content line shares a leading indent -> indent SILENTLY stripped.

Exits non-zero while the defect is present; exits zero once the emitter
round-trips both cases.
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


def _parse(text):
    res = parse_frontmatter(text)
    return res[0] if isinstance(res, tuple) else res


ok = True

# --- Case A: first line more-indented than the rest -------------------
val_a = "  indented first\nsecond line"
text_a = emit_frontmatter({"title": "x", "definition_of_done": val_a})
print("=== EMITTED A ===")
print(text_a)
try:
    back_a = _parse(text_a)
    got_a = (back_a.get("definition_of_done") or "").rstrip("\n")
    print("=== RE-PARSE A ok, dod repr ===")
    print(repr(got_a))
    if got_a != val_a:
        print("FAIL A: round-trip mismatch")
        ok = False
except Exception as e:  # noqa: BLE001
    print("=== RE-PARSE A RAISED ===")
    print(f"{type(e).__name__}: {e}")
    print("FAIL A: emitted block scalar does not re-parse")
    ok = False

# --- Case B: every line shares a leading indent -----------------------
val_b = "  - [ ] nested\n  - [ ] second"
text_b = emit_frontmatter({"title": "x", "definition_of_done": val_b})
back_b = _parse(text_b)
got_b = (back_b.get("definition_of_done") or "").rstrip("\n")
print("=== ROUND-TRIP B ===")
print("ORIGINAL :", repr(val_b))
print("ROUNDTRIP:", repr(got_b))
if got_b != val_b:
    print("FAIL B: leading whitespace silently stripped")
    ok = False

print()
print("RESULT:", "PASS — emitter round-trips leading whitespace" if ok
      else "FAIL — block-scalar emitter mangles leading whitespace")
sys.exit(0 if ok else 1)
