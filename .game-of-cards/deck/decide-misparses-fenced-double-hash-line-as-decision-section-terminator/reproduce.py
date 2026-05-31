"""Reproduce: DECISION_REQUIRED_RE misparses fenced `## ` lines.

The regex at goc/engine.py:366-369 terminates the `## Decision required`
section at any `^## ` line, even when that line sits inside a fenced
code block. `goc decide` therefore truncates the archived deliberation
and corrupts the rewritten README.

Exits 1 (defect fires) until a fence-aware parse lands.
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

from goc.engine import extract_decision_required_section, replace_or_append_decision

BODY = """## Decision required

Choose between:

```bash
## install via brew
brew install something
```

Both options have tradeoffs.

## Why it matters

Production deploys depend on this.
"""

archived = extract_decision_required_section(BODY)
resolved = replace_or_append_decision(BODY, "Pick brew", "Simpler", "2026-05-30")

print("=== archived (log.md) ===")
print(repr(archived))
print()
print("=== resolved README ===")
print(resolved)
print("=== end ===")

failures: list[str] = []

if "Both options have tradeoffs" not in (archived or ""):
    failures.append(
        "archived deliberation is truncated — 'Both options have tradeoffs.' "
        "was dropped from the log.md archive (regex terminated at the fenced "
        "`## install via brew` line)."
    )

if "## install via brew" in resolved.split("## Decision", 1)[-1]:
    failures.append(
        "resolved README carries a stray `## install via brew` heading below "
        "the `## Decision` block — the fenced code-block line was misparsed "
        "as a section boundary and left orphaned after the substitution."
    )

if "```" in resolved and resolved.count("```") % 2 == 1:
    failures.append(
        "rewritten README has an unbalanced count of ``` fences — opening "
        "fence was consumed by the regex match while the closing fence "
        "remains in place."
    )

if failures:
    print()
    print("DEFECT FIRES:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print()
print("OK — fence-aware parse holds; archived deliberation is complete and "
      "the rewritten README has no stray heading or orphaned fence.")
sys.exit(0)
