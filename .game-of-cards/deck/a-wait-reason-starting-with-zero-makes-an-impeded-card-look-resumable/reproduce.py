#!/usr/bin/env python3
"""Leading-zero `waiting_on` — the two SessionStart hook ports disagree with
the engine about whether the card is impeded.

`goc._vendor.yaml_lite._INT_RE` was narrowed on 2026-06-28 (card
`yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values`) so a
leading-zero run like `007` stays a *string* instead of coercing to int 8. The
two hook ports that explicitly document themselves as mirroring that constant
still carry the pre-narrowing `^-?\\d+$`, so they coerce `007` away and read the
card as carrying no impediment — while `engine.waiting_impedes` says it does.

Exits 0 when every port agrees with the engine; 1 otherwise.
"""
from __future__ import annotations

import importlib.util
import re
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402

HOOK_TEMPLATE = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"
TS_ENTRY = ROOT / "openclaw-plugin" / "index.ts"
TS_BUNDLE = ROOT / "openclaw-plugin" / "dist" / "index.js"

# Bare frontmatter tokens whose int-vs-string classification the mirrors must
# match. Leading-zero runs are the drifted set.
CASES = ["007", "00", "0123", "0", "-0", "42", "-7", "external"]

CARD = """\
---
title: c
summary: s
status: active
stage: null
contribution: medium
created: 2026-01-01
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: []
waiting_on: {value}
definition_of_done: |
  - [ ] x
---

# c
"""


def _load_hook():
    spec = importlib.util.spec_from_file_location("_goc_hook", HOOK_TEMPLATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    hook = _load_hook()
    failures = 0

    print(f"engine  yaml_lite._INT_RE = {yaml_lite._INT_RE.pattern}")
    print(f"python  hook _INT_RE      = {hook._INT_RE.pattern}")
    m = re.search(r"^const INT_RE = /(.+)/;$", TS_ENTRY.read_text(), re.MULTILINE)
    ts_pattern = m.group(1) if m else "(not found)"
    print(f"openclaw index.ts INT_RE  = {ts_pattern}")
    print()

    canonical = yaml_lite._INT_RE.pattern
    if hook._INT_RE.pattern != canonical:
        print(f"[FAIL] {HOOK_TEMPLATE.relative_to(ROOT)}: _INT_RE does not mirror "
              f"yaml_lite._INT_RE")
        failures += 1
    if ts_pattern != canonical:
        print(f"[FAIL] {TS_ENTRY.relative_to(ROOT)}: INT_RE does not mirror "
              f"yaml_lite._INT_RE")
        failures += 1
    if TS_BUNDLE.exists() and f"var INT_RE = /{canonical}/;" not in TS_BUNDLE.read_text():
        print(f"[FAIL] {TS_BUNDLE.relative_to(ROOT)}: shipped bundle carries a "
              f"stale INT_RE (rebuild with `npm run build`)")
        failures += 1
    print()

    tmp = Path(tempfile.mkdtemp())
    card_dir = tmp / "c"
    card_dir.mkdir()
    readme = card_dir / "README.md"

    print(f"{'waiting_on':<12} {'engine':<10} {'python hook':<12} verdict")
    print(f"{'-' * 12} {'-' * 10} {'-' * 12} -------")
    for value in CASES:
        readme.write_text(CARD.format(value=value))
        eng = engine.waiting_impedes(engine.load_card(card_dir))
        hk = hook._is_impeded(readme)
        ok = eng == hk
        if not ok:
            failures += 1
        print(f"{value:<12} {str(eng):<10} {str(hk):<12} {'ok' if ok else '[FAIL] disagree'}")

    print()
    if failures:
        print(f"[FAIL] {failures} divergence(s) — a leading-zero wait reason is "
              f"announced as resumable while the engine impedes the card")
        return 1
    print("[PASS] every port agrees with the engine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
