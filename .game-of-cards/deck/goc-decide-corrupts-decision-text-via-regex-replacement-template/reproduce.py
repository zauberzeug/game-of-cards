"""Proof that `replace_or_append_decision` mishandles backslash escapes.

`goc decide --decision "..." --reasoning "..."` routes user text into
`replace_or_append_decision`, which embeds it in `block` and hands `block`
to `re.sub` as the *replacement template*. Python's re engine then parses
backslash sequences in that template: `\\1` becomes a group back-reference,
`\\p` raises `re.error`. Both corrupt or crash a legitimate decision.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
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

from goc.engine import replace_or_append_decision  # noqa: E402

BODY = "## Decision required\n\nPick a path.\n"
failures = 0

# Variant A — crash: a Windows-style path contains an invalid escape (\p).
try:
    replace_or_append_decision(BODY, r"Use C:\path", "x", "2026-05-27")
    print("[A] no crash (decision text with C:\\path accepted)")
except Exception as e:  # noqa: BLE001
    failures += 1
    print(f"[A] CRASH: decision 'Use C:\\path' raised {type(e).__name__}: {e}")

# Variant B — silent corruption: \1 expands to captured group 1.
out = replace_or_append_decision(BODY, r"go \1 ahead", "reason", "2026-05-27")
expected_fragment = "go \\1 ahead"
if expected_fragment in out:
    print("[B] decision text preserved verbatim")
else:
    failures += 1
    print("[B] CORRUPTED: literal 'go \\1 ahead' not found; output was:")
    print("    " + repr(out))

print()
if failures:
    print(f"DEFECT CONFIRMED: {failures}/2 variants mangled the decision text.")
    sys.exit(1)
print("No defect: both variants preserved the decision text.")
