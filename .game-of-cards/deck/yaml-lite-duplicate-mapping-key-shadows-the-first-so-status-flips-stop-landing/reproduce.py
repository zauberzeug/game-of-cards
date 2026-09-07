#!/usr/bin/env python3
"""Reproduce: a repeated key in a yaml-lite mapping silently shadows the first
copy instead of raising, and the engine's three readers then disagree about
which copy is authoritative.

Exits non-zero while the defect is present (the duplicate is swallowed), exits
zero once the parser raises ParseError as it already does for the analogous
tab / over-indent / missing-space-after-colon cases.

The demonstration block below is informational: it prints the reader split
(parser last-wins vs `mutate_frontmatter_field` first-wins) that makes a
`goc status ... active` claim report success and land nothing. It does not
gate the exit code — once the parser raises, that split is unreachable.
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

from goc._vendor.yaml_lite import ParseError, safe_load  # noqa: E402
from goc.engine import mutate_frontmatter_field, parse_frontmatter  # noqa: E402

FAILURES = []

# Case 1: block mapping with a repeated key — the first value is dropped.
doc1 = 'title: foo\nstatus: open\ntags: [bug]\nstatus: done'
try:
    out = safe_load(doc1)
    FAILURES.append(
        f"duplicate block-mapping key did NOT raise; returned {out!r} "
        "(expected ParseError; the first `status: open` was silently dropped)"
    )
    print(f"DEFECT: safe_load({doc1!r})\n     -> {out!r}")
except ParseError:
    print(f"OK: safe_load({doc1!r}) raised ParseError")

# Case 2: flow mapping with a repeated key — same silent shadowing, the shape
# `worker: {who: a, where: b}` travels through.
doc2 = "worker: {who: alice, where: main, who: bob}"
try:
    out = safe_load(doc2)
    FAILURES.append(
        f"duplicate flow-mapping key did NOT raise; returned {out!r} "
        "(expected ParseError; `who: alice` was silently dropped)"
    )
    print(f"DEFECT: safe_load({doc2!r})\n     -> {out!r}")
except ParseError:
    print(f"OK: safe_load({doc2!r}) raised ParseError")

# Control: the analogous over-indent case already raises (fail-loud posture).
try:
    safe_load("a: 1\n  b: 2")
    FAILURES.append("control over-indent did NOT raise (parser posture regression)")
except ParseError:
    print("OK (control): over-indented line raises ParseError")

# ── Demonstration: the reader split the silent shadowing produces ────────────
CARD = (
    "---\n"
    "title: dup-status\n"
    'summary: "A card that acquired a second status key in a clean merge."\n'
    "status: open\n"
    "human_gate: none\n"
    "tags: [bug]\n"
    "status: open\n"
    "---\n"
    "\n"
    "# dup-status\n"
)
try:
    fm, _body = parse_frontmatter(CARD)
except Exception as exc:  # noqa: BLE001 - any parse refusal means the fix landed
    print(f"\nreader-split demonstration unreachable (parse refused): {exc}")
else:
    claimed = mutate_frontmatter_field(CARD, "status", "active")
    fm_after, _ = parse_frontmatter(claimed)
    first_line = next(
        line for line in claimed.splitlines() if line.startswith("status:")
    )
    print("\nreader split on a card carrying two `status:` keys:")
    print(f"  goc status ... active rewrote the FIRST copy   -> {first_line!r}")
    print(f"  the parser keeps the LAST copy                 -> status={fm_after['status']!r}")
    print("  => the verb prints 'open -> active', commits, and the card stays open")

if FAILURES:
    print("\nFAILED:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)

print("\nAll checks passed: a repeated mapping key fails loud.")
sys.exit(0)
