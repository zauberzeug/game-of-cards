#!/usr/bin/env python3
"""Reproduce: the backfill script writes `closed_at` bare, bypassing `_yaml_inline`.

Two independent probes, both derived from the repo rather than hardcoded:

  1. STATIC — every `mutate_frontmatter_field(..., "closed_at", X)` call site in
     the repo is checked for whether `X` routes through `_yaml_inline`. The four
     engine sites do; `scripts/backfill_terminal_closed_at.py` does not. This is
     the sweep gap left by the closed card
     `closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter`,
     whose DoD claimed "any other call site of `mutate_frontmatter_field` for a
     colon-bearing value either route the value through `_yaml_inline` first or
     document the intentional bare form".

  2. BEHAVIORAL — the script's exact write expression is applied to a synthetic
     terminal card, then the result is re-parsed and re-emitted through
     `emit_frontmatter`. The bare line the script writes differs from the line
     the emitter produces for the same value, so the next full-frontmatter
     rewrite (`goc decide`, `goc migrate-list-style`, `goc repair-edges`)
     silently re-quotes a card nobody edited.

Exit 1 while the defect fires; exit 0 once the script routes the timestamp
through `_yaml_inline` (or documents an intentional bare form).

PyYAML is deliberately not used — the project declares no dependencies and
ships a vendored `yaml_lite`, so a real-YAML probe would not run on a clean
checkout.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc.engine import (  # noqa: E402
    _yaml_inline,
    emit_frontmatter,
    mutate_frontmatter_field,
    parse_frontmatter,
)

# `GOC_BACKFILL_SRC` points the probe at an alternate copy of the script, so the
# pre-fix behaviour stays checkable after the fix lands:
#   git show <pre-fix-rev>:scripts/backfill_terminal_closed_at.py > /tmp/before.py
#   GOC_BACKFILL_SRC=/tmp/before.py uv run python .../reproduce.py   # exits 1
BACKFILL = Path(
    os.environ.get("GOC_BACKFILL_SRC")
    or ROOT / "scripts" / "backfill_terminal_closed_at.py"
)
ENGINE = ROOT / "goc" / "engine.py"

# Matches `mutate_frontmatter_field(<text>, "closed_at", <value>)` and captures
# the value expression, so the probe reads the real call sites instead of a
# hand-maintained list that would drift. The value alternation tolerates one
# level of nested call parens (`_yaml_inline(_utc_now_iso())`).
CALL_RE = re.compile(
    r'mutate_frontmatter_field\(\s*[^,]+,\s*"closed_at"\s*,\s*'
    r"(?P<value>(?:[^()]|\((?:[^()]|\([^()]*\))*\))+?)\s*\)"
)

def _rel(path: Path) -> str:
    """Repo-relative label, or the bare path when `GOC_BACKFILL_SRC` points out of tree."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


failures: list[str] = []
backfill_value_expr: str | None = None

# ── Probe 1: static sweep over every closed_at writer ──────────────────────
print("== Probe 1: does every `closed_at` writer route through `_yaml_inline`? ==\n")
print(f"{'site':52}  {'value expression':34}  routed")
print(f"{'-' * 52}  {'-' * 34}  ------")

for path in (ENGINE, BACKFILL):
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        m = CALL_RE.search(line)
        if not m:
            continue
        value = m.group("value").strip()
        routed = "_yaml_inline" in value
        site = f"{_rel(path)}:{lineno}"
        print(f"{site:52}  {value:34}  {'yes' if routed else 'NO'}")
        if path == BACKFILL:
            backfill_value_expr = value
        if not routed:
            failures.append(f"{site} passes {value} without _yaml_inline")

print()
if failures:
    print(f"[FAIL] {len(failures)} closed_at writer(s) bypass the emitter quote contract:")
    for f in failures:
        print(f"        {f}")
else:
    print("[OK]   every closed_at writer routes through _yaml_inline")

# ── Probe 2: the bare line the script writes vs. the line the emitter emits ─
print("\n== Probe 2: does the written line survive a full-frontmatter rewrite? ==\n")

# Reproduce the script's own timestamp shape (backfill_terminal_closed_at.py
# `latest_readme_commit_iso`) from a fixed instant, so the probe is stable.
ts = datetime(2026, 5, 29, 9, 58, 40, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

card = (
    "---\n"
    "title: synthetic-disproved-card\n"
    "summary: A synthetic terminal card used only by this probe.\n"
    "status: disproved\n"
    "stage: null\n"
    "contribution: low\n"
    'created: "2026-05-01T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [x] TDD: probe fixture\n"
    "---\n"
    "\n"
    "# synthetic-disproved-card\n"
)

# The script's write path — the value expression is taken from the script's own
# source (captured in Probe 1) and evaluated against this probe's `ts`, so the
# probe cannot pass while the real call site is still wrong, and cannot fail
# once the real call site is fixed. A hand-copied expression here would decouple
# the probe from the code it is meant to check.
if backfill_value_expr is None:
    raise RuntimeError(
        f"no `mutate_frontmatter_field(..., \"closed_at\", ...)` call found in "
        f"{_rel(BACKFILL)} — the probe's assumption about the "
        f"script's write path no longer holds; re-read the script."
    )
script_value = eval(backfill_value_expr, {"_yaml_inline": _yaml_inline, "ts": ts})  # noqa: S307
script_text = mutate_frontmatter_field(card, "closed_at", script_value)
script_line = next(l for l in script_text.splitlines() if l.startswith("closed_at:"))

# The engine's closure write path (engine.py:4296 / 4393 / 5336).
engine_text = mutate_frontmatter_field(card, "closed_at", _yaml_inline(ts))
engine_line = next(l for l in engine_text.splitlines() if l.startswith("closed_at:"))

# What a later full-frontmatter rewrite would emit for the script's own card.
fm, body = parse_frontmatter(script_text)
rewritten = emit_frontmatter(fm)
emitter_line = next(l for l in rewritten.splitlines() if l.startswith("closed_at:"))

print(f"  backfill script writes : {script_line}")
print(f"  engine closure writes  : {engine_line}")
print(f"  emit_frontmatter emits : {emitter_line}")
print()

drift = script_line != emitter_line
if drift:
    print("[FAIL] the script's line differs from the emitter's line for the same value —")
    print("       the next `goc decide` / `migrate-list-style` / `repair-edges` rewrite")
    print("       re-quotes this card with no authored change.")
    failures.append("script line != emit_frontmatter line for the same closed_at value")
else:
    print("[OK]   the script's line is byte-identical to the emitter's line")

# The value itself must still round-trip regardless of form — this guards the
# fix from over-correcting into a quoted-but-wrong value.
assert fm["closed_at"] == ts, f"value corrupted: {fm['closed_at']!r} != {ts!r}"
print(f"\n  value round-trips unchanged either way: {fm['closed_at']!r}")

print(f"\n{'DEFECT REPRODUCED' if failures else 'DEFECT FIXED'} "
      f"({len(failures)} failing check(s))")
sys.exit(1 if failures else 0)
