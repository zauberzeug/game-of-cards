"""Proof that `goc move`'s bare-slug rewrite over-matches.

`_move_text_rewrite` is meant to rewrite genuine card cross-references.
Its fifth form — the bare-slug regex — anchors only on `[-\\w]`, so a slug
that abuts a `.`, `/`, `(`, or `:` is treated as a standalone token. That
means a card slug coinciding with a URL path segment, a dotted filename, or
a code identifier gets silently rewritten across EVERY tracked file in the
repo, not just card bodies.

Run: uv run python .game-of-cards/deck/move-rewrites-card-slug-inside-urls-paths-and-code-identifiers/reproduce.py
Exit 0 == defect fixed (no over-rewrite). Exit 1 == defect present.
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

from goc.engine import _move_text_rewrite  # noqa: E402

# (text, old_slug, new_slug, label) — none of these texts contain a genuine
# card cross-reference; the slug appears only inside a URL / path / identifier.
NON_REFERENCE_CASES = [
    ("function add-cli() in script.sh", "add-cli", "add-command", "shell function name"),
    ("GET /v1/user-api/list", "user-api", "user-rest", "URL path segment"),
    ("see http://x.com/foo-bar.html", "foo-bar", "baz", "URL with dotted file"),
    ("the file my-tool.py imports", "my-tool", "renamed", "dotted filename stem"),
]

# A genuine bare prose mention that SHOULD still be rewritten, to show the
# form is not simply useless — the fix must preserve this.
GENUINE_CASE = (
    "see the card foo-bar for context",
    "foo-bar",
    "baz",
    "expected 'see the card baz for context'",
)

failures = []
print("=== Non-reference contexts (must NOT be rewritten) ===")
for text, old, new, label in NON_REFERENCE_CASES:
    out = _move_text_rewrite(text, old, new)
    over_rewritten = out != text
    print(f"  [{label}]")
    print(f"    in : {text!r}")
    print(f"    out: {out!r}")
    print(f"    -> {'OVER-REWRITTEN (bug)' if over_rewritten else 'left intact (ok)'}")
    if over_rewritten:
        failures.append(label)

print("\n=== Genuine prose mention (SHOULD be rewritten) ===")
gtext, gold, gnew, gnote = GENUINE_CASE
gout = _move_text_rewrite(gtext, gold, gnew)
print(f"  in : {gtext!r}")
print(f"  out: {gout!r}  ({gnote})")

print()
if failures:
    print(f"DEFECT PRESENT: {len(failures)} non-reference context(s) over-rewritten: {failures}")
    sys.exit(1)
print("OK: no non-reference context over-rewritten.")
sys.exit(0)
