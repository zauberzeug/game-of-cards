"""Reproduce: `goc quality-pass --llm` counts a title/summary verdict with
`ok: false` but NO `rewrite` string as a "proposed rewrite", while the apply
path never offers it.

`_render_verdict` sets has_rewrite=True whenever a title/summary verdict's
`ok` is falsy — regardless of whether a `rewrite` string is present — so
`rewrite_count` (reported as "N with proposed rewrites") over-counts.
`_apply_verdict_interactive` guards the actual mutation with
`not ...ok() and ...get("rewrite")`, so the two sides disagree.

Run: uv run python .game-of-cards/deck/.../reproduce.py
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

from goc.engine import _apply_verdict_interactive, _render_verdict  # noqa: E402


class _FakeCard:
    """Minimal stand-in; apply path short-circuits before touching it."""

    title = "some-card"
    path = Path("/nonexistent")


# A verdict where the LLM said the title is NOT ok but supplied no rewrite
# string (e.g. it flagged a problem it could not auto-fix, or returned a
# partial/malformed verdict). Same for summary. No DoD issues.
verdict = {
    "title": "some-card",
    "title_verdict": {"ok": False, "reason": "jargon-y but no fix offered"},
    "summary_verdict": {"ok": False, "reason": "too long but no rewrite offered"},
    "dod_issues": [],
}

# --- render side: what the count is built from ---
buf = io.StringIO()
with redirect_stdout(buf):
    has_rewrite = _render_verdict(verdict)
rendered = buf.getvalue()

# --- apply side: what is actually offered/applied (auto_yes => accept all) ---
applied = _apply_verdict_interactive(_FakeCard(), verdict, auto_yes=True)

print("=== _render_verdict ===")
print(f"has_rewrite (counts toward 'N with proposed rewrites'): {has_rewrite}")
print(f"printed a title REWRITE line:   {'title:   REWRITE' in rendered}")
print(f"printed a summary REWRITE line: {'summary: REWRITE' in rendered}")
print(f"printed 'proposed: ?' (no real rewrite): {'proposed: ?' in rendered}")
print()
print("=== _apply_verdict_interactive (auto_yes) ===")
print(f"applied: {applied}")
print()

over_counts = has_rewrite and not (applied["title"] or applied["summary"] or applied["dod"])
print(f"BUG: render counts a rewrite the apply path never offers? {over_counts}")
sys.exit(0 if over_counts else 1)
