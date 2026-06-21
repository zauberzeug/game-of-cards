"""Reproduce: _sync_claude_import overwrites a user-authored @CLAUDE.local.md
import with GoC's briefing target.

A user's pre-existing CLAUDE.md that imports their own @CLAUDE.local.md should
survive `goc install --briefing-target AGENTS.md` (the default). Instead the
union-match in _sync_claude_import rewrites that line to @AGENTS.md.

Exits non-zero while the defect is present (the user import is destroyed);
exits zero once the fix preserves it.
"""

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

import goc.install as I  # noqa: E402

USER_IMPORT = "@CLAUDE.local.md"

cases = []

# CASE A: CLAUDE.md is the user's sole @CLAUDE.local.md import line.
d_a = Path(tempfile.mkdtemp())
(d_a / "CLAUDE.md").write_text(USER_IMPORT + "\n")
I._sync_claude_import(d_a, "AGENTS.md")
text_a = (d_a / "CLAUDE.md").read_text()
cases.append(("A (sole @CLAUDE.local.md)", text_a, USER_IMPORT in text_a))

# CASE B: custom content plus the user's bare @CLAUDE.local.md import.
d_b = Path(tempfile.mkdtemp())
(d_b / "CLAUDE.md").write_text("# Project rules\n\nUse tabs.\n\n" + USER_IMPORT + "\n")
I._sync_claude_import(d_b, "AGENTS.md")
text_b = (d_b / "CLAUDE.md").read_text()
cases.append(("B (custom content + @CLAUDE.local.md)", text_b, USER_IMPORT in text_b))

all_ok = True
for label, text, preserved in cases:
    print(f"CASE {label}:")
    print(f"  result: {text!r}")
    print(f"  user import preserved? {preserved}")
    if not preserved:
        all_ok = False

if all_ok:
    print("\nPASS: user-authored @CLAUDE.local.md import preserved in all cases.")
    sys.exit(0)
else:
    print("\nFAIL: _sync_claude_import overwrote a user-authored import line.")
    sys.exit(1)
