"""Reproduce: the `log-md-closure-entry` derived check rejects a closure
heading whose separator is an ASCII hyphen (`-`) instead of the em-dash
(`—`) the skill template prescribes — and reports it as *missing* rather
than mis-punctuated.

Run: uv run python .game-of-cards/deck/attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing/reproduce.py
"""

import re
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

from goc.engine import _date_part  # noqa: E402

# This is the exact pattern `_run_derived_check` compiles for the
# `log-md-closure-entry` check (engine.py, name == "log-md-closure-entry").
today = "2026-06-29T10:00:00Z"
date_prefix = _date_part(today)
pattern = re.compile(
    rf"^## {re.escape(date_prefix)}(?:T\d{{2}}:\d{{2}}:\d{{2}}Z)? — Closure",
    re.MULTILINE,
)

# A closer who wrote a genuine, well-formed closure entry, but typed an
# ASCII hyphen (the character most editors/agents emit by default) where
# the template shows a Unicode em-dash.
log_with_ascii_hyphen = (
    "## 2026-06-25 — earlier journal entry\n\n"
    "Some history.\n\n"
    "## 2026-06-29 - Closure\n\n"          # ASCII hyphen, not em-dash
    "- **What changed**: engine.py:1 — fixed the thing\n"
    "- **Verification**: 641 tests pass\n"
)

# The same entry written exactly as the template prescribes (em-dash).
log_with_em_dash = log_with_ascii_hyphen.replace(
    "## 2026-06-29 - Closure", "## 2026-06-29 — Closure"
)

hit_hyphen = bool(pattern.search(log_with_ascii_hyphen))
hit_emdash = bool(pattern.search(log_with_em_dash))

# Mirror the human-facing message the check returns on a miss.
miss_message = f"no '## {date_prefix} — Closure' section"

print("A closure section IS present in both logs (greppable for ' Closure'):")
print(f"  ascii-hyphen log has a Closure heading: {'## 2026-06-29 - Closure' in log_with_ascii_hyphen}")
print(f"  em-dash    log has a Closure heading:   {'## 2026-06-29 — Closure' in log_with_em_dash}")
print()
print("Derived-check verdict (True = PASS, the check finds a closure entry):")
print(f"  em-dash heading      -> {hit_emdash}")
print(f"  ascii-hyphen heading -> {hit_hyphen}")
print()
print("On the ascii-hyphen log the check FAILS with the message:")
print(f'  "{miss_message}"')
print("  ...even though a closure section is plainly present — the diagnostic")
print("  claims the section is MISSING when it is only mis-punctuated.")
print()

defect = (hit_emdash is True) and (hit_hyphen is False)
print(f"DEFECT REPRODUCED: {defect}")
sys.exit(0 if defect else 1)
