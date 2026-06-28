"""Reproduce: `_load_consuming_repo_tags` crashes (unhashable element)
or silently pollutes the tag set (hashable non-string element) when a
`canonical_tags:` list in `.game-of-cards/canonical-tags.md` contains a
non-string element.

After the fix, the loader filters list elements to `str`:
- the unhashable case returns only the valid string tag (no TypeError),
- the hashable-non-string case drops the int/bool members.

Exits 0 when the defect is gone; exits 1 (and prints the offending
behavior) while the bug is present.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest import mock


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


def _load(body: str):
    with tempfile.TemporaryDirectory() as tmp:
        game_dir = Path(tmp) / ".game-of-cards"
        game_dir.mkdir()
        (game_dir / "canonical-tags.md").write_text(body)
        with mock.patch.object(engine, "DECK_ROOT", Path(tmp)):
            return engine._load_consuming_repo_tags()


def main() -> int:
    ok = True

    # Failure mode 1: unhashable element -> TypeError crash.
    unhashable = "```yaml\ncanonical_tags:\n  - good-tag\n  - [nested, list]\n```\n"
    try:
        result = _load(unhashable)
        print(f"unhashable element: RESULT: {result}")
        if result != {"good-tag"}:
            print("  EXPECTED {'good-tag'} (non-string element filtered)")
            ok = False
    except Exception as exc:  # noqa: BLE001
        print(f"unhashable element: CRASH: {type(exc).__name__} {exc}")
        ok = False

    # Failure mode 2: hashable non-string elements -> silent pollution.
    hashable = "```yaml\ncanonical_tags:\n  - good-tag\n  - 123\n  - true\n```\n"
    try:
        result = _load(hashable)
        print(f"hashable non-string elements: RESULT: {result}")
        if result != {"good-tag"}:
            print("  EXPECTED {'good-tag'} (int/bool elements dropped)")
            ok = False
    except Exception as exc:  # noqa: BLE001
        print(f"hashable non-string elements: CRASH: {type(exc).__name__} {exc}")
        ok = False

    if ok:
        print("PASS: non-string list elements are filtered, not crashed/added")
        return 0
    print("FAIL: defect present")
    return 1


if __name__ == "__main__":
    sys.exit(main())
