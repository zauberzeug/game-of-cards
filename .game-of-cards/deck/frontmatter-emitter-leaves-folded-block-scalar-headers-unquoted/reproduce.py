"""Reproduce: the frontmatter emitter writes folded block-scalar headers
that carry an explicit indent (>2, >3, >2-, ...) bare, so the card crashes
on the next re-parse.

The emitter quote-trigger `_YAML_BLOCK_HEADER_RE` allows a digit run on the
pipe branch (`\\|\\d*[-+]?`) but NOT on the folded branch (`>[-+]?`). The
yaml-lite parser's folded recognizer `_FOLDED_INDICATOR_RE = ^>(\\d+)?([-+]?)$`
does accept the digits and raises "folded scalars (>) not supported".

Run on a clean checkout:
    uv run python .game-of-cards/deck/frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted/reproduce.py
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

# Folded-with-explicit-indent values that the parser recognizes as block
# headers. Each is a plausible free-text scalar (e.g. a summary fragment).
FOLDED = [">2", ">3", ">10", ">2-", ">2+"]
# The pipe siblings are already correctly quoted by the prior fix; included
# as the control group that must keep round-tripping.
PIPE = ["|2", "|3", "|2-"]

failures = []
for val in FOLDED + PIPE:
    fm = {"title": "t", "status": "open", "summary": val}
    emitted = emit_frontmatter(fm)
    summary_line = next(l for l in emitted.splitlines() if l.startswith("summary:"))
    try:
        parsed, _body = parse_frontmatter(emitted)
        ok = parsed.get("summary") == val
        verdict = "OK" if ok else f"MISMATCH -> {parsed.get('summary')!r}"
        if not ok:
            failures.append(val)
    except Exception as exc:  # noqa: BLE001
        verdict = f"CRASH: {type(exc).__name__}: {exc}"
        failures.append(val)
    print(f"  {val!r:8} emitted as {summary_line!r:22} round-trip: {verdict}")

print()
if failures:
    print(f"DEFECT REPRODUCED: {len(failures)} value(s) failed round-trip: {failures}")
    sys.exit(1)
print("No defect: every block-scalar-shaped value round-trips.")
sys.exit(0)
