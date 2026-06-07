#!/usr/bin/env python3
"""Reproduce: _write_skills_source un-comments a documentation example
instead of rewriting the active `skills_source:` key when both exist.

A config that carries BOTH a commented documentation example
(`# skills_source: auto`) AND an active setting (`skills_source: vendored`)
should have its ACTIVE line rewritten when the engine pins a new mode.
Instead, the single `#?`-optional pattern + `count=1` matches whichever
line appears first in document order. When the comment precedes the
active line, the comment is un-commented and the real active setting is
left stale — yielding TWO active `skills_source:` keys with conflicting
values (invalid/ambiguous YAML; the requested switch silently fails).

Exit 0 == defect ABSENT (active line rewritten, no duplicate key).
Exit 1 == defect PRESENT.
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

import tempfile

from goc.install import _write_skills_source


def _run_case(label: str, config_text: str, value: str, expected: str) -> bool:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        (target / ".game-of-cards").mkdir()
        cfg = target / ".game-of-cards" / "config.yaml"
        cfg.write_text(config_text)
        _write_skills_source(target, value)
        got = cfg.read_text()

    active_lines = [
        ln for ln in got.splitlines()
        if ln.lstrip().startswith("skills_source")
        and not ln.lstrip().startswith("#")
    ]
    ok = got == expected
    print(f"--- {label}")
    print(f"  value requested : {value}")
    print(f"  input           : {config_text!r}")
    print(f"  output          : {got!r}")
    print(f"  expected        : {expected!r}")
    print(f"  active key count : {len(active_lines)} (want exactly 1)")
    print(f"  match           : {ok}")
    print()
    return ok


def main() -> int:
    # Documentation example comment FIRST, active setting SECOND.
    # Switching to `plugin` must rewrite the ACTIVE line and leave the
    # comment as a comment (so there is exactly one active key).
    case1 = _run_case(
        "commented doc example above an active key; switch vendored->plugin",
        "# skills_source: auto\n\nskills_source: vendored\n",
        "plugin",
        "# skills_source: auto\n\nskills_source: plugin\n",
    )

    # Sanity: comment-only config (no active line) must still un-comment.
    case2 = _run_case(
        "comment-only config; un-comment to active key",
        "# skills_source: auto\n",
        "plugin",
        "skills_source: plugin\n",
    )

    print("=" * 60)
    if case1 and case2:
        print("PASS: active key rewritten, no duplicate key (defect absent).")
        return 0
    print("FAIL: defect present — comment un-commented, active key left stale.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
