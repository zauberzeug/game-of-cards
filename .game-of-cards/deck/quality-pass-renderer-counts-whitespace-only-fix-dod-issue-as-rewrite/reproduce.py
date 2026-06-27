"""Reproduce: _render_verdict counts a whitespace-only-`fix` DoD issue as a
proposed rewrite, diverging from _apply_dod_rewrite which skips it.

Run on a clean checkout:
    uv run python deck/<title>/reproduce.py   (or .game-of-cards/deck/...)

Exits non-zero while the defect is live (renderer says has_rewrite=True for a
whitespace-only fix), exits zero once the renderer mirrors the apply guard.
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

verdict = {
    "title": "x",
    "title_verdict": {"ok": True},
    "summary_verdict": {"ok": True},
    "dod_issues": [{"idx": 0, "issue": "vague item", "fix": "   "}],
}

buf = io.StringIO()
with redirect_stdout(buf):
    has_rewrite = engine._render_verdict(verdict)
rendered = buf.getvalue()

# What the apply path would actually do with the same input: a whitespace-only
# `fix` is filtered out, so nothing would be rewritten.
apply_would_write = {
    issue["idx"]: issue["fix"]
    for issue in verdict["dod_issues"]
    if "idx" in issue and "fix" in issue and issue["fix"].strip()
}

print("render output:")
print(rendered.rstrip())
print(f"has_rewrite (renderer)      = {has_rewrite}")
print(f"apply path would write      = {apply_would_write}  (empty -> no rewrite)")

if has_rewrite and not apply_would_write:
    print(
        "\nFAIL: renderer counts this as a rewrite (has_rewrite=True) but the "
        "apply path writes nothing — render/apply disagree on a whitespace-only fix."
    )
    sys.exit(1)

print("\nPASS: renderer agrees with the apply path (whitespace-only fix is not a rewrite).")
sys.exit(0)
