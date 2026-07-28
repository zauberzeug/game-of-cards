#!/usr/bin/env python3
"""A bare apostrophe in a flow field + a trailing inline comment = card lost.

`_strip_comment` only gates quote-mode entry on a node-start position for a
*bare quoted scalar* (`text[:1]` is a quote). Inside a flow collection it
still flips quote-mode on ANY quote char, so the apostrophe in `o'connor`
opens a run that never closes, the trailing ` # comment` is never stripped,
and `_parse_flow_mapping` then rejects the value as "trailing content".

`parse_frontmatter` turns that into a FrontmatterError, and `load_card`
downgrades it to a WARNING — the card silently disappears from every deck
view.

Exits 0 once the flow arm carries the same node-start gate `_split_flow`
already has.
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

from goc import engine  # noqa: E402
from goc._vendor import yaml_lite  # noqa: E402

CARD = """---
title: probe-card
summary: "probe"
status: open
stage: null
contribution: high
created: "2026-07-26T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
worker: {who: o'connor, where: main} # temp owner
definition_of_done: |
  - [ ] TDD: something
---

# probe-card
"""

failures = 0

# --- 1. the control: same value, no inline comment -> parses fine ----------
control = yaml_lite.safe_load("worker: {who: o'connor, where: main}\n")
print(f"control  (no comment):  worker={control['worker']!r}")
if control["worker"] != {"who": "o'connor", "where": "main"}:
    print("  [FAIL] control should parse cleanly")
    failures += 1

# --- 2. the defect: add a space-preceded inline comment --------------------
line = "worker: {who: o'connor, where: main} # temp owner\n"
try:
    got = yaml_lite.safe_load(line)
    print(f"defect   (+ comment):  worker={got['worker']!r}")
    if got["worker"] != {"who": "o'connor", "where": "main"}:
        print("  [FAIL] comment not stripped; worker corrupted")
        failures += 1
except ValueError as exc:
    print(f"defect   (+ comment):  ParseError: {exc}")
    print("  [FAIL] a space-preceded ' #' comment must be stripped")
    failures += 1

# --- 3. the symptom: the whole card drops out of the deck ------------------
try:
    fm, _body = engine.parse_frontmatter(CARD)
    print(f"card     parse:        worker={fm.get('worker')!r}")
    if fm.get("worker") != {"who": "o'connor", "where": "main"}:
        print("  [FAIL] card frontmatter did not round-trip")
        failures += 1
except engine.FrontmatterError as exc:
    print(f"card     parse:        FrontmatterError: {exc}")
    print("  [FAIL] card is unreadable -> load_card warns and skips it, so it")
    print("         vanishes from the queue, the board, triage and validate")
    failures += 1

# --- 4. regressions the fix must not break ---------------------------------
regressions = [
    ("bare scalar comment", "title: don't  # note\n", "title", "don't"),
    ('quoted scalar keeps "#"', 'a: "x \\" y # z"\n', "a", 'x " y # z'),
    ("flow seq + comment", "tags: [bug, infra] # note\n", "tags", ["bug", "infra"]),
    ('flow "#" in quoted elem', 'tags: ["a # b", c]\n', "tags", ["a # b", "c"]),
    ("flow ']' in quoted elem", 'tags: ["a]b # x", c]\n', "tags", ["a]b # x", "c"]),
    ("doubled '' in quoted", "k: 'don''t # x'\n", "k", "don't # x"),
]
for label, text, key, want in regressions:
    try:
        got = yaml_lite.safe_load(text)[key]
    except ValueError as exc:
        got = f"ParseError: {exc}"
    ok = got == want
    print(f"regress  {label:24} -> {got!r} {'ok' if ok else '[FAIL] want ' + repr(want)}")
    if not ok:
        failures += 1

print()
print(f"failures: {failures}")
sys.exit(1 if failures else 0)
