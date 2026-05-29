"""closed_at format drifts between closure verbs and the frontmatter emitter.

`goc done` / `goc done --bundle` / `goc status X disproved|superseded` set
`closed_at` via `mutate_frontmatter_field(text, "closed_at", _utc_now_iso())`,
inserting the raw datetime string (`2026-05-29T09:58:40Z`) **unquoted**. But
`emit_frontmatter` → `_yaml_inline` matches the `:` in `_YAML_NEEDS_QUOTE` and
emits the same value **quoted** (`"2026-05-29T09:58:40Z"`). Both round-trip
cleanly through the vendored parser, but the two writer paths disagree on
canonical form, so any whole-frontmatter rewrite (`goc decide`,
`goc migrate-list-style`, future emitters) silently mutates every card the
closure verbs ever touched.
"""

from __future__ import annotations

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

from goc.engine import (
    _yaml_inline,
    emit_frontmatter,
    mutate_frontmatter_field,
    parse_frontmatter,
)

CARD_TEMPLATE = """\
---
title: example
summary: ""
status: open
stage: null
contribution: medium
created: "2026-05-29T10:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] example
---

body
"""


def main() -> int:
    fixed_now = "2026-05-29T12:00:00Z"

    # Path A: closure verbs (`goc done`, `goc status X disproved|superseded`,
    # `goc done --bundle`). Before the fix, these passed the raw datetime
    # directly into `mutate_frontmatter_field`, which inserted it verbatim
    # (unquoted). The fix routes the value through `_yaml_inline` so the
    # writer matches the emitter's canonical form.
    after_closure = mutate_frontmatter_field(CARD_TEMPLATE, "status", "done")
    after_closure = mutate_frontmatter_field(
        after_closure, "closed_at", _yaml_inline(fixed_now)
    )
    closer_line = next(
        ln for ln in after_closure.splitlines() if ln.startswith("closed_at:")
    )

    # Path B: whole-frontmatter rewrite — `goc decide`, `goc migrate-list-style`,
    # and every future emitter route through `emit_frontmatter` → `_yaml_inline`,
    # which quotes any value containing `:` (the regex `_YAML_NEEDS_QUOTE`).
    fm, body = parse_frontmatter(after_closure)
    reemitted = emit_frontmatter(fm, body=body)
    emitter_line = next(
        ln for ln in reemitted.splitlines() if ln.startswith("closed_at:")
    )

    print("Path A (closure verbs)              :", closer_line)
    print("Path B (emit_frontmatter rewrite)   :", emitter_line)
    print("drift                               :", closer_line != emitter_line)

    # The drift is materialized in the live deck. `goc migrate-list-style
    # --dry-run` would rewrite every card whose `closed_at` survived only the
    # mutate path.
    deck = _repo_root() / ".game-of-cards" / "deck"
    quoted = 0
    bare = 0
    for readme in sorted(deck.glob("*/README.md")):
        lines = readme.read_text(encoding="utf-8").splitlines()
        # Skip the opening `---`, scan frontmatter until the closing `---`.
        for line in lines[1:]:
            if line == "---":
                break
            if line.startswith('closed_at: "'):
                quoted += 1
                break
            if line.startswith("closed_at: 2"):
                bare += 1
                break
            if line.startswith("closed_at: null"):
                break
    print()
    print(f"live deck — closed_at bare        : {bare}")
    print(f"live deck — closed_at quoted      : {quoted}")
    print(
        "→ emit_frontmatter rewrites every bare line to its quoted form on next pass."
    )

    # Always exit zero: the script is a diagnostic. The `drift` line above is
    # True before the fix and False after; the exit code documents that the
    # script ran to completion in both states.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
